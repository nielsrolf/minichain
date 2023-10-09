import asyncio
import json
import os
import traceback
import uuid
from collections import defaultdict
from typing import Any, Dict, Optional
import shutil

import yaml
from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pydantic.error_wrappers import ValidationError
from starlette.websockets import WebSocketDisconnect

from minichain.dtypes import (AssistantMessage, Cancelled, FunctionMessage,
                              SystemMessage, UserMessage)
from minichain.message_handler import MessageDB
from minichain.utils.json_datetime import datetime_converter



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
        shutil.copyfile(file, new_path)
        file = new_path
    return f"displaying file: {file}"


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("websocket accepted")

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
            return
        try:
            message = json.loads(json.dumps(message, default=datetime_converter))
            await websocket.send_json(message)
        except Exception as e:
            breakpoint()
            import traceback
            traceback.print_exc()

    
    message_db.add_consumer(send_message_raise_cancelled, is_main=True)
    

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
            print("agent_name", agent_name)
            agent = agents[agent_name]

            conversation = message_db.get(payload.response_to)
            await agent.run(query=payload.query, conversation=conversation)


    except Exception as e:
        traceback.print_exc()


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/agents")
async def get_agents():
    return list(agents.keys())


@app.get("/messages/{path:path}")
async def read_messages(path: str):
    if path == "":
        path = "root"
    path = path.split('/')
    conversation = message_db.get(path[-1])
    if conversation:
        return conversation.as_json()
    else:
        raise HTTPException(status_code=404, detail="Conversation not found")


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
