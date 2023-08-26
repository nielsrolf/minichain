import json
import os
import traceback
import uuid
from collections import defaultdict
from typing import Any, Dict, Optional
import asyncio

from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pydantic.error_wrappers import ValidationError

from minichain.agent import (AssistantMessage, FunctionMessage, SystemMessage,
                             UserMessage)
from minichain.agents.chatgpt import ChatGPT
from minichain.agents.planner import Planner
from minichain.agents.programmer import Programmer
from minichain.agents.webgpt import SmartWebGPT, WebGPT


class MessageDB:
    def __init__(self, path=".minichain/"):
        self.path = path
        os.makedirs(f"{path}/messages", exist_ok=True)
        os.makedirs(f"{path}/logs", exist_ok=True)
        self.load()

    def load(self):
        path = self.path
        self.messages = self.load_dir_as_list(f"{path}/messages")
        self.logs = self.load_dir_as_list(f"{path}/logs")

    def load_dir_as_list(self, path):
        messages = []
        paths = os.listdir(path)
        paths_sorted = sorted(paths, key=lambda x: int(x.split(".")[0]))
        for filename in paths_sorted:
            try:
                with open(os.path.join(path, filename), "r") as f:
                    message = json.load(f)
                    # message = classes[message.get('role', None)](**message)
                    messages.append(message)
            except Exception as e:
                print(f"Error loading message from {filename}", e)
        return messages

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
        dir_items = self.__dict__[dirname]
        def get_id(d):
            if "id" in d:
                return d["id"]
            return f"{d['type']}-{d['conversation_id']}"
        try:
            pos = [get_id(i) for i in dir_items].index(get_id(message))
            dir_items[pos] = message
        except ValueError:
            pos = len(dir_items)
            dir_items.append(message)
        path = f"{self.path}/{dirname}"
        filename = f"{pos}.json"
        with open(os.path.join(path, filename), "w") as f:
            json.dump(message, f)

    def add_message(self, message):
        if not isinstance(message, dict):
            message = message.dict()
        self.save_msg(message, "logs")
        if "role" in message:
            self.save_msg(message, "messages")

    def get_history(self, conversation_id, no_init=False):
        dicts = self.get_conversation(conversation_id)
        if no_init:
            dicts = [i for i in dicts if i.get("is_init", False) == False]
        else:
            for i in dicts:
                i.pop("is_init", None)
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
    response_to: Optional[str] = None
    agent: str


message_db = MessageDB()


agents = {}

class Cancelled(Exception):
    pass


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Create a websocket that sends:
    {type: start, conversation_id: 123}
    {...message, id: 1},
    {...message, id: 2},
    {...message, id: 3}
    {type: start, conversation_id: 456}
    {...message, id: 5}
    {type: end, conversation_id: 123}
    """
    await websocket.accept()
    print("websocket accepted")

    # replay logs
    print("replay logs", message_db.logs)
    print("start/end conversation", [i for i in message_db.logs if i.get("type", None) in ["start", "end"]])
    for message in message_db.logs:
        if not isinstance(message, dict):
            message = message.dict()
        await websocket.send_json(message)

    async def add_message_to_db_and_send(message: dict):
        print("add_message_to_db_and_send", message)
        message_db.add_message(message)
        if not isinstance(message, dict):
            message = message.dict()
        # check the websocket: has a cancel message been sent? if no message has been sent, avoid blocking by using asyncio.wait
        try:
            data = await asyncio.wait_for(websocket.receive_text(), timeout=0.01)
            if data == "cancel":
                raise Cancelled("cancel")
        except asyncio.TimeoutError:
            pass
        except Cancelled as e:
            raise e
        except RuntimeError as e:
            print(".. hopefully just websocket closed, running in background", e, type(e))
            return

        try:
            await websocket.send_json(message)
        except Exception as e:
            print("websocket closed, running in background")
    try:
        while True:
            data = await websocket.receive_text()
            print("received data", data)
            try:
                payload = Payload(**json.loads(data))
            except ValidationError as e:
                # probably a heart beat
                continue
            agent_name = payload.agent
            if agent_name not in agents:
                await websocket.send_text(f"Agent {agent_name} not found")
                continue

            history = message_db.get_history(payload.response_to, no_init=True)
            
            print("agent_name", agent_name )
            agent = agents[agent_name]
            print("agent", agent)
            agent.on_message_send = add_message_to_db_and_send
            conversation_id = payload.response_to or f"root.{uuid.uuid4().hex[:5]}"
            print("CALLING:", payload.dict(), conversation_id)
            response = await agent.run(query=payload.query, history=history, conversation_id=conversation_id)
            
    except Exception as e:
        traceback.print_exc()

        # await websocket.send_json(response.dict())
        # except Exception as e:
        #     await websocket.send_text(str(e))
        #     continue


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.on_event("startup")
async def preload_agents():
    """This function should run after the async event loop has started."""
    agents.update(
        {
            "webgpt": WebGPT(),
            "smartgpt": SmartWebGPT(),
            "yopilot": Programmer(),
            "planner": Planner(),
            "chatgpt": ChatGPT(),
        }
    )
    for agent in list(agents.values()):
        agents[agent.name] = agent


def start(port=8000):
    import uvicorn
    uvicorn.run(app, host="localhost", port=port)


# We want to run this via python -m minichain.api
if __name__ == "__main__":
    start()
