import asyncio
import json
import os
import traceback
import uuid
from collections import defaultdict
from typing import Any, Dict, Optional

import yaml
from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pydantic.error_wrappers import ValidationError
from starlette.websockets import WebSocketDisconnect

from minichain.dtypes import (AssistantMessage, Cancelled, FunctionMessage,
                              SystemMessage, UserMessage)
from minichain.streaming import Stream


class MessageDB:
    def __init__(self, path=".minichain"):
        self.path = path
        os.makedirs(f"{path}/messages", exist_ok=True)
        self.saved_ids = {}
        self.childrenOf = defaultdict(list)
        self.conversationAgents = {}
        self.messages = []
        self.load()

    def load(self):
        path = f"{self.path}/messages"
        messages = []
        paths = os.listdir(path)
        paths_sorted = sorted(paths, key=lambda x: int(x.split(".")[0]))
        for filename in paths_sorted:
            try:
                with open(os.path.join(path, filename), "r") as f:
                    message = json.load(f)
                    if message.get("stack", None):
                        self.update_childrenOf(message)
                    else:
                        messages.append(message)
                        self.saved_ids[message["id"]] = filename
            except Exception as e:
                print(f"Error loading message from {filename}", e)
        self.messages = messages

    def update_childrenOf(self, message):
        parent = message["stack"][0]
        for child in message["stack"][1:]:
            if child not in self.childrenOf[parent]:
                self.childrenOf[parent].append(child)
                if message.get("agent", None) is not None:
                    self.conversationAgents[child] = message["agent"]
            parent = child
    
    def get_path(self, id):
        # return the conversation stack to the conversation of the message id
        path = []
        while id != "root":
            path = [id] + path
            id = [i for i in self.childrenOf if id in self.childrenOf[i]][0]
        return ["root"] + path

    def dicts_to_classes(self, dicts):
        classes = {
            "user": UserMessage,
            "system": SystemMessage,
            "function": FunctionMessage,
            "assistant": AssistantMessage,
            None: dict,
        }
        messages = []
        for message in dicts:
            message = classes[message.get("role", None)](**message)
            messages.append(message)
        return messages

    def save_msg(self, message, dirname):
        if not message.get("id") in self.saved_ids:
            path = f"{self.path}/{dirname}"
            filename = f"{len(os.listdir(path))}.json"
            filepath = os.path.join(path, filename)
            if (
                message.get("id", None) is not None
            ):  # could also be a stack message, which has no id
                self.saved_ids[message["id"]] = filepath
        else:
            filepath = self.saved_ids[message["id"]]
        with open(filepath, "w") as f:
            json.dump(message, f)

    def add_message(self, message):
        if not isinstance(message, dict):
            message = message.dict()
        if message.get("stack", None):
            self.update_childrenOf(message)
        else:
            # if the message is new, append it
            if message.get("id") not in self.saved_ids:
                self.messages.append(message)
            else:
                # if the message is already saved, update it
                for i, m in enumerate(self.messages):
                    if m["id"] == message["id"]:
                        self.messages[i] = message
        self.save_msg(message, "messages")

    def get_history(self, conversation_id):
        dicts = self.get_conversation(conversation_id)
        return self.dicts_to_classes(dicts)

    def get_message(self, message_id):
        for message in self.messages:
            if message["id"] == message_id:
                return message
        return None

    def get_conversation(self, conversation_id):
        conversation = []
        for message in self.messages:
            if message["conversation_id"] == conversation_id:
                conversation.append(message)
        return conversation

    def messages_as_dicts(self):
        dicts = []
        for message in self.messages:
            if not isinstance(message, dict):
                message = message.dict()
            dicts.append(message)
        return dicts


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


class Payload(BaseModel):
    query: str
    response_to: Optional[str] = "root"
    agent: str


message_db = MessageDB()


agents = {}


from pydantic import BaseModel, Field

from minichain.functions import tool
from minichain.utils.docker_sandbox import bash


@tool()
async def upload_file_to_chat(
    file: str = Field(..., description="The path to the file to upload."),
):
    """Upload a file to the chat."""
    # if the file is not in the cwd or a sub dir, we need to copy it to a download folder
    full_path = os.path.abspath(file)
    if not full_path.startswith(os.getcwd()):
        # copy it to ./minichain/downloads/{len(os.listdir('./minichain/downloads'))}/{filename}
        filename = os.path.basename(file)
        downloads_path = "./minichain/downloads"
        os.makedirs(downloads_path, exist_ok=True)
        new_path = f"{downloads_path}/{len(os.listdir(downloads_path))}_{filename}"
        await bash(
            [f"cp {file} {new_path}"],
            session=(
                os.getcwd().replace("/", "")
                .replace(".", "")
                .replace("-", "")
                .replace("_", "")
                .replace(" ", "")
            )
        )
        file = new_path
    return f"displaying file: {file}"


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Create a websocket that sends:
    {type: stack, stack: [123, 1]}
    {type: message, data {id: 1, content: 'yo'},
    {type: stack, stack: [123, 3, 456, 2]}
    {type: chunk, diff: {"content": "hello", id: 2}
    {type: chunk, diff: {"content": "world", id: 2}
    {type: message, data: {id: 2, ...final message}}
    """
    await websocket.accept()
    print("websocket accepted")

    async def add_message_to_db_and_send(message: dict):
        """message: {id: 1, content: 'yo'} / {stack: [123, 1]}"""
        print("add_message_to_db_and_send", message)
        message_db.add_message(message)
        if not isinstance(message, dict):
            message = message.dict()
        if message.get("stack", None):
            await send_message_raise_cancelled({"type": "stack", **message})
        else:
            await send_message_raise_cancelled({"type": "message", "data": message})

    async def add_chunk(chunk, message_id):
        message = {"diff": chunk, "id": message_id, "type": "chunk"}
        await send_message_raise_cancelled(message)

    async def send_message_raise_cancelled(message):
        # check the websocket: has a cancel message been sent? if no message has
        # been sent, avoid blocking by using asyncio.wait_for
        try:
            data = await asyncio.wait_for(websocket.receive_text(), timeout=0.01)
            if data == "cancel":
                raise Cancelled("cancel")
        except asyncio.TimeoutError:
            pass
        except Cancelled as e:
            raise e
        except (WebSocketDisconnect, RuntimeError) as e:
            pass
        try:
            await websocket.send_json(message)
        except Exception as e:
            print("websocket closed, running in background")

    try:
        while True:
            try:
                data = await websocket.receive_text()
            except Exception:
                # sleep for a bit and try again
                await asyncio.sleep(1)
                continue
            print("received data", data)
            try:
                payload = Payload(**json.loads(data))
                if not payload.response_to:
                    payload.response_to = "root"
            except ValidationError as e:
                # probably a heart beat
                continue
            agent_name = payload.agent
            if agent_name not in agents:
                await websocket.send_text(f"Agent {agent_name} not found")
                continue

            if payload.response_to == "root":
                history = []
            else:
                history = message_db.get_history(payload.response_to)
                conversation_stack = message_db.get_path(payload.response_to)

            print("agent_name", agent_name)
            agent = agents[agent_name]
            stream = Stream(on_message=add_message_to_db_and_send, on_chunk=add_chunk)

            with await stream.conversation(
                payload.response_to, agent=agent.name
            ) as stream:
                if payload.response_to == "root":
                    with await stream.to([], role="user") as stream:
                        await stream.set(payload.query)
                else:
                    stream.conversation_stack = conversation_stack

                agent.register_stream(stream)
                await agent.run(query=payload.query, history=history)

            # go to cwd if the agent has a bash
            try:
                await agent.interpreter.bash(
                    commands=[f"cd {agent.interpreter.bash.cwd}"]
                )
            except Exception as e:
                try:
                    await agent.programmer.interpreter.bash(
                        commands=[f"cd {os.getcwd()}"]
                    )
                except Exception as e:
                    pass

    except Exception as e:
        traceback.print_exc()


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/agents")
async def get_agents():
    return list(agents.keys())


@app.get("/history")
async def get_history():
    return {
        "messages": message_db.messages_as_dicts(),
        "childrenOf": message_db.childrenOf,
        "conversationAgents": message_db.conversationAgents,
    }


@app.get("/static/{path:path}")
async def static(path):
    print("static", path)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path)


@app.on_event("startup")
async def preload_agents():
    """This function should run after the async event loop has started."""
    # load the ./minichain/settings.yml file
    if not os.path.exists(".minichain/settings.yml"):
        # copy the default settings file from the modules install dir (minichain/default_settings.yml) to the cwd ./minichain/settings.yml
        print("Copying default settings file to .minichain/settings.yml")
        os.makedirs(".minichain", exist_ok=True)
        import shutil

        shutil.copyfile(
            os.path.join(os.path.dirname(__file__), "default_settings.yml"),
            ".minichain/settings.yml",
        )

    with open(".minichain/settings.yml", "r") as f:
        settings = yaml.load(f, Loader=yaml.FullLoader)

    # load the agents
    for agent_name, agent_settings in settings.get("agents", {}).items():
        if not agent_settings.get("display", False):
            continue
        print("Loading agent", agent_name)
        class_name = agent_settings.pop("class")
        # class name is e.g. minichain.agents.programmer.Programmer
        # import the agent class
        module_name, class_name = class_name.rsplit(".", 1)
        module = __import__(module_name, fromlist=[class_name])
        agent_class = getattr(module, class_name)
        # create the agent
        agent = agent_class(**agent_settings.get("init", {}))
        # add the agent to the agents dict
        agents[agent_name] = agent

    for agent in list(agents.values()):
        agent.functions.append(upload_file_to_chat)
    for agent in list(agents.values()):
        agents[agent.name] = agent


def start(port=8745):
    import uvicorn

    uvicorn.run(app, host="localhost", port=port)


# We want to run this via python -m minichain.api
if __name__ == "__main__":
    start()
