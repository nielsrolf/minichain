import asyncio
import json

import websockets


async def heartbeat(websocket):
    while True:
        await websocket.send(json.dumps({"type": "heartbeat"}))
        await asyncio.sleep(1)  # Send a heartbeat every 10 seconds.


async def websocket_client():
    uri = "ws://localhost:8745/ws/webgpt"  # Replace with your server URL and agent name

    async with websockets.connect(uri) as websocket:
        # Start the heartbeat task
        asyncio.create_task(heartbeat(websocket))

        payload = {
            "query": "what is the latest post on r/programmerhumor?",
        }

        # Send initial payload
        await websocket.send(json.dumps(payload))

        try:
            while True:
                response = await websocket.recv()
                print(response)
        except websockets.exceptions.ConnectionClosed:
            print("The server closed the connection")
        except KeyboardInterrupt:
            print("Client closed the connection")


# Run the client
if __name__ == "__main__":
    asyncio.run(websocket_client())
