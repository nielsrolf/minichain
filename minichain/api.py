import json
from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pydantic.error_wrappers import ValidationError
from typing import Any, Dict
from minichain.agent import SystemMessage, UserMessage, FunctionMessage, AssistantMessage
from minichain.agents.webgpt import WebGPT, SmartWebGPT
from minichain.agents.programmer import Programmer
from minichain.agents.planner import Planner
from minichain.agents.chatgpt import ChatGPT
from fastapi import WebSocket
from collections import defaultdict
from typing import Optional
import traceback
import os
import uuid


class MessageDB:
    def __init__(self, path=".minichain"):
        self.messages = []
        self.logs = []
        self.path = path
        os.makedirs(path, exist_ok=True)
        self.load()
    
    def load(self):
        path = self.path
        classes = {
            "user": UserMessage,
            "assistant": AssistantMessage,
            "system": SystemMessage,
            "function": FunctionMessage,
        }
        try:
            with open(os.path.join(path, "messages.json"), "r") as f:
                messages = json.load(f)
                self.messages = [classes[i['role']](**i) for i in messages]
            with open(os.path.join(path, "logs.json"), "r") as f:
                self.logs = json.load(f)
        except FileNotFoundError:
            print("No messages found")
        except Exception as e:
            print("Error loading messages", e)
    
    def save(self):
        path = self.path
        with open(os.path.join(path, "messages.json"), "w") as f:
            json.dump([i.dict() for i in self.messages], f)
        with open(os.path.join(path, "logs.json"), "w") as f:
            json.dump(self.logs, f)
    
    # save on exit
    def __del__(self):
        self.save()

    def add_message(self, message):
        self.logs.append(message)
        if not isinstance(message, dict):
            # The message can either be a dict with control messages ({'type': 'start', 'conversation_id': '10055'})
            # or a pydantic model (UserMessage, SystemMessage, ...).
            # We only want to store the messages here.
            self.messages.append(message)
    
    def get_history(self, conversation_id):
        return self.get_conversation(conversation_id)

    def get_message(self, message_id):
        for message in self.messages:
            if message.id == message_id:
                return message
        raise Exception(f"Message {message_id} not found")
    
    def get_conversation(self, conversation_id):
        conversation = []
        for message in self.messages:
            if message.conversation_id == conversation_id:
                conversation.append(message)
        return conversation
    

    
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
    expose_headers=['*'],
)


class Payload(BaseModel):
    query: str
    response_to: Optional[str] = None


agents = {
    "webgpt": WebGPT,
    "smartgpt": SmartWebGPT,
    "yopilot": Programmer,
    "planner": Planner,
    "chatgpt": ChatGPT,
}


message_db = MessageDB()




@app.websocket("/ws/{agent_name}")
async def websocket_endpoint(websocket: WebSocket, agent_name: str):
    """Create a websocket that sends:
    {type: start, conversation_id: 123}
    {...message, id: 1},
    {...message, id: 2},
    {...message, id: 3}
    {type: start, conversation_id: 456}
    {type: "start", id: 4}
    h
    e
    r
    e

    c
    o
    ...
    {...message, id: 4} # message finished
    {type: end, conversation_id: 456}
    {...message, id: 5}
    {type: end, conversation_id: 123}
    """
    await websocket.accept()

    # replay logs
    for message in message_db.logs:
        if not isinstance(message, dict):
            message = message.dict()
        await websocket.send_json(message)

    async def add_message_to_db_and_send(message: dict):
        print("add_message_to_db_and_send", message)
        message_db.add_message(message)
        if not isinstance(message, dict):
            message = message.dict()
        await websocket.send_json(message)

    async def on_stream_starts(message: dict):
        await websocket.send_json({"type": "start", "id": message["id"], "parent": message["parent"]})

    async def on_stream_ends(message: dict):
        await websocket.send_json(message)

    async def on_stream_message(char):
        await websocket.send_text(char)


    try:
        while True:
            data = await websocket.receive_text()
            print("received data", data)
            try:
                payload = Payload(**json.loads(data))
            except ValidationError as e:
                # probably a heart beat
                continue        
            if agent_name not in agents:
                await websocket.send_text(f"Agent {agent_name} not found")
                continue
            
            init_history = message_db.get_history(payload.response_to)
            rootId = payload.response_to # TODO get the conv id of the response_to message
            if payload.response_to is None:
                rootId = uuid.uuid4().hex[:5]
                await websocket.send_json({"type": "start", "conversation_id": rootId})
                init_message = {"role": "user", "content": payload.query, "conversation_id": rootId, "id": uuid.uuid4().hex[:5]}
                message_db.add_message(init_message)
                await websocket.send_json(init_message)

            # try:
            agent = agents[agent_name](
                init_history=init_history,
                on_message_send=add_message_to_db_and_send, 
                on_stream_starts=on_stream_starts,
                on_stream_ends=on_stream_ends,
                on_stream_message=on_stream_message,
            )
            response = await agent.run(query=payload.query)
            final_message = {"role": "assistant", "conversation_id": rootId, "id": uuid.uuid4().hex[:5], "content": response}
            # db
            message_db.add_message(final_message)
            await websocket.send_json(final_message)
            await websocket.send_json({"type": "end", "conversation_id": rootId})

    except Exception as e:
        traceback.print_exc()

        # await websocket.send_json(response.dict())
        # except Exception as e:
        #     await websocket.send_text(str(e))
        #     continue


@app.get("/")
async def root():
    return {"message": "Hello World"}


def start():
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)

# We want to run this via python -m minichain.api
if __name__ == "__main__":
    start()