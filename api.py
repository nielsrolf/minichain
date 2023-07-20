import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Dict
from minichain.agents.webgpt import SmartWebGPT
from minichain.agents.programmer import Programmer
from fastapi import WebSocket
from collections import defaultdict
from typing import Optional
import traceback

class MessageDB:
    def __init__(self):
        self.messages = []

    def add_message(self, message):
        if not isinstance(message, dict):
            self.messages.append(message)
    
    def get_history(self, message_id):
        if message_id is None:
            return None
        for message in self.messages:
            if message["id"] == message_id:
                if message["parent"] is None:
                    return [message]
                else:
                    return self.get_history(message["parent"]) + [message]
        raise HTTPException(status_code=404, detail="Message not found")
    

app = FastAPI()


class Payload(BaseModel):
    query: str
    response_to: Optional[str] = None


agents = {
    "webgpt": SmartWebGPT,
    "yopilot": Programmer
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


    while True:
        try:
            data = await websocket.receive_text()
            print("received data", data)
            payload = Payload(**json.loads(data))
            
            if agent_name not in agents:
                await websocket.send_text(f"Agent {agent_name} not found")
                continue
            
            init_history = message_db.get_history(payload.response_to)

            # try:
            agent = agents[agent_name](
                init_history=init_history,
                on_message_send=add_message_to_db_and_send, 
                on_stream_starts=on_stream_starts,
                on_stream_ends=on_stream_ends,
                on_stream_message=on_stream_message,
            )
            response = await agent.run(query=payload.query)
        except Exception as e:
            traceback.print_exc()

        # await websocket.send_json(response.dict())
        # except Exception as e:
        #     await websocket.send_text(str(e))
        #     continue


@app.get("/")
async def root():
    return {"message": "Hello World"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)
