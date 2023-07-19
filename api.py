import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Dict
from minichain.agents.webgpt import SmartWebGPT
from minichain.agents.programmer import Programmer
from fastapi import WebSocket
from collections import defaultdict


app = FastAPI()


class Payload(BaseModel):
    query: str
    response_to: str = None

agents = {
    "WebGPT": SmartWebGPT,
    "yopilot": Programmer
}


class MessageDB:
    def __init__(self):
        self.messages = []

    def add_message(self, message):
        self.messages.append(message)
    
    def get_history(self, message_id):
        # We want to get the history from the session of the message, up to the message itself
        history = []
        # find the session that contains the message
        for session in self.sessions.values():
            if message_id in [m.id for m in session]:
                break
        # Now, get the history
        for message in session:
            history.append(message)
            if message.id == message_id:
                break
        if len(history) == 0:
            return None
        return history


message_db = MessageDB()


@app.websocket("/ws/{agent_name}")
async def websocket_endpoint(websocket: WebSocket, agent_name: str):
     """Create a websocket that sends:
    {...message, id: 1},
    {...message, id: 2},
    {...message, id: 3}
    {type: "start", id: 4}
    h
    e
    r
    e

    c
    o
    ...
    {...message, id: 4} # message finished
    """
    await websocket.accept()

    async def add_message_to_db_and_send(message: dict):
        message_db.add_message(message)
        await websocket.send_json(message)

    async def on_stream_starts(message: dict):
        await websocket.send_json({"type": "start", "id": message["id"], "parent": message["parent"]})

    async def on_stream_ends(message: dict):
        await websocket.send_json(message)

    async def on_stream_message(char):
        await websocket.send_text(char)


    while True:
        data = await websocket.receive_text()
        payload = Payload(**json.loads(data))
        
        if agent_name not in agents:
            await websocket.send_text(f"Agent {agent_name} not found")
            continue
        
        init_history = message_db.get_history(payload.response_to)
        
        try:
            agent = agents[agent_name](
                init_history=init_history,
                on_message_send=add_message_to_db_and_send, 
                on_stream_starts=on_stream_starts,
                on_stream_ends=on_stream_ends,
                on_stream_message=on_stream_message,
            )
            response = agent.run(query=payload.query)
            await websocket.send_json(response)
        except Exception as e:
            await websocket.send_text(str(e))
            continue
