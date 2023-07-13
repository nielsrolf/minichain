from agent import Agent, UserMessage
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI()

# Mount the static files directory for serving HTML and JavaScript
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

agent = Agent()  # Create an instance of your Agent class


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    while True:
        # Receive message from the client
        message = await websocket.receive_text()

        # Create a UserMessage object from the received message
        user_message = UserMessage(content=message)

        # Pass the user message to your agent and get the response
        response = agent.handle_message(user_message)

        # Send the response back to the client
        await websocket.send_text(response)


@app.get("/")
async def get():
    return templates.TemplateResponse("index.html", {"request": request})
