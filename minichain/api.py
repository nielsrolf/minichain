import asyncio
from typing import List
import json
import os
import uuid
from typing import Any, Dict, Optional
import shutil
from pydantic import BaseModel, Field
import yaml
from fastapi import FastAPI, HTTPException, WebSocket, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from minichain.dtypes import ConsumerClosed, FunctionCall, UserMessage
from minichain.functions import tool
from minichain.message_handler import MessageDB
from minichain.utils.json_datetime import datetime_converter
from minichain.auth import get_token_payload, create_access_token



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
    query: Optional[str] = None
    response_to: Optional[str] = "root"
    agent: str
    function_call: Optional[Dict[str, Any]] = None


class Execute(BaseModel):
    code: str
    type: str = "python"
    insert_after: List[str]


class MessagePayload(BaseModel):
    role: Optional[str] = None
    content: Optional[str] = None
    function_call: Optional[Dict[str, Any]] = None


message_db = MessageDB()
agents = {}


@app.get("/")
async def root():
    return {"message": "Hello World"}


class ShareRequest(BaseModel):
    conversation_id: str
    type: str = "view"


def check_permission_return_item(token_payload, item_id=None, permission='edit'):
    """Check if the user has the permission to access the item."""
    if permission == 'edit' and permission not in token_payload['scopes']:
        raise HTTPException(status_code=401, detail="Not enough permissions")
    if item_id is None:
        return
    message_or_conversation = message_db.get(item_id)
    if message_or_conversation is None:
        message_or_conversation = message_db.get_message(item_id)
    if message_or_conversation is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return message_or_conversation


@app.post("/share/")
async def share(share_request: ShareRequest, token_payload: dict = Depends(get_token_payload)):
    """Create a new token that can be used to access the conversation."""
    conversation = check_permission_return_item(token_payload, share_request.conversation_id, share_request.type)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"token": create_access_token({"sub": "frontend", "scopes": [share_request.conversation_id, share_request.type]})}


@app.get("/agents")
async def get_agents(token_payload: dict = Depends(get_token_payload)):
    return list(agents.keys())


@app.get("/byagent/{agent}")
async def get_conversations_by_agent(agent: str, token_payload: dict = Depends(get_token_payload)):
    if "root" not in token_payload['scopes']:
        # return the conversation that the user has access to
        conversation = message_db.get(token_payload['scopes'][0])
        return conversation.as_json()
    messages = message_db.as_json(agent)
    return messages


@app.get("/messages/{path:path}")
async def read_messages(path: str, token_payload: dict = Depends(get_token_payload)):
    if path == "":
        path = "root"
    path = path.split('/')
    # conversation = message_db.get(path[-1])
    conversation = check_permission_return_item(token_payload, path[-1], 'view')
    if conversation:
        return conversation.as_json()
    else:
        raise HTTPException(status_code=404, detail="Conversation not found")


@app.put("/meta/{path:path}")
async def put_meta(path: str, meta: Dict[str, Any], token_payload: dict = Depends(get_token_payload)):
    if path == "":
        path = "root"
    path = path.split('/')
    check_permission_return_item(token_payload, path[-1], 'edit')
    message_or_conversation = await message_db.update_meta(path[-1], meta)
    return message_or_conversation.as_json()


@app.get("/meta/{path:path}")
async def get_meta(path: str, token_payload: dict = Depends(get_token_payload)):
    if path == "":
        path = "root"
    path = path.split('/')
    if path[-1] == "root":
        return {"path": ["root"]}
    message_or_conversation = check_permission_return_item(token_payload, path[-1], 'view')
    return message_or_conversation.meta


@app.put("/chat/{path:path}")
async def put_chat(path: str, update: MessagePayload, token_payload: dict = Depends(get_token_payload)):
    if path == "":
        path = "root"
    path = path.split('/')
    update = update.dict()
    check_permission_return_item(token_payload, path[-1], 'edit')
    message = await message_db.update_message(path[-1], update)
    return message.as_json()


@app.get("/fork/{path:path}")
async def fork(path: str, token_payload: dict = Depends(get_token_payload)):
    path = path.split('/')
    conversation = check_permission_return_item(token_payload, path[-2], 'edit')
    new_path = conversation.path + [uuid.uuid4().hex[:8]]
    forked_conversation = conversation.fork(path[-1], new_path)
    return forked_conversation.as_json()


@app.get("/static/{path:path}")
async def static(path, token_payload: dict = Depends(get_token_payload)):
    print("static", path)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path)



@app.post("/run/")
async def run_cell(cell: Execute, token_payload: dict = Depends(get_token_payload)):
    """Run a cell and insert the function call output after the specified cell."""
    conversation = check_permission_return_item(token_payload, cell.insert_after[-2], 'edit')
    print("running cell", cell)
    # get the conversation
    conversation = conversation.at(cell.insert_after[-1])
    # get the agent
    agent = agents[conversation.meta['agent']]

    session = await agent.session(conversation)

    function_call = FunctionCall(
        name="jupyter",
        arguments={"code": cell.code, "type": cell.type},
    )
    # result = await session.execute_action(function_call)
    asyncio.create_task(session.execute_action(function_call))
    return {"message": "success"}


@app.post("/cell/")
async def create_cell(cell: Execute, token_payload: dict = Depends(get_token_payload)):
    """Create a cell."""
    # get the conversation
    conversation = check_permission_return_item(token_payload, cell.insert_after[-2], 'edit')
    conversation = conversation.at(cell.insert_after[-1])

    function_call = FunctionCall(
        name="jupyter",
        arguments={"code": cell.code, "type": cell.type},
    )

    message = UserMessage(
        content="",
        function_call=function_call,
    )

    await conversation.send(message)
    return {"message": "success"}



@app.get("/cancel/{conversation_id}")
async def cancel_agent(conversation_id: str, token_payload: dict = Depends(get_token_payload)):
    """Cancel an agent."""
    conversation = check_permission_return_item(token_payload, conversation_id, 'edit')
    message_db.cancel(conversation_id)


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


@app.post("/message/")
async def run_agent(payload: Payload, token_payload: dict = Depends(get_token_payload)):
    """Run an agent."""

    conversation = check_permission_return_item(token_payload, payload.response_to, 'edit')

    agent_name = payload.agent
    if agent_name not in agents:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    agent = agents[agent_name]

    # start the agent.run in the background, so we can return the conversation id
    session = await agent.session(conversation)

    # send the message
    message = UserMessage(
        content=payload.query,
        function_call=payload.function_call,
    )
    await session.conversation.send(message)
    asyncio.create_task(session.run_until_done())
    return {"path": session.conversation.path}


@app.websocket("/ws/{conversation_id}")
async def websocket_endpoint(websocket: WebSocket, conversation_id: str):
    await websocket.accept()
    print("websocket accepted")
    # wait for the token
    try:
        token = await websocket.receive_text()
        print("websocket token", token)
        token_payload = get_token_payload(token)
        print("websocket token_payload", token_payload)
    except Exception as e:
        print("websocket error", e)
        raise HTTPException(status_code=401, detail="Invalid token")
    if conversation_id == "root":
        # we close the websocket, because we don't want to send the root messages
        await websocket.close()
        return

    async def send_to_websocket(message):
        message = json.loads(json.dumps(message, default=datetime_converter))
        try:
            await websocket.send_json(message)
        except Exception as e:
            print("websocket error", e)
            raise ConsumerClosed()
        
    conversation = message_db.get(conversation_id)
    for message in conversation.messages:
        await send_to_websocket({
            "type": "set",
            "chat": message.chat,
            "meta": message.meta,
            "id": message.path[-1],
            "path": message.path,
        })
    
    message_db.add_consumer(send_to_websocket, conversation_id)

    # avoid closing the websocket
    while True:
        await asyncio.sleep(1)
        if websocket.client_state == 3:
            print("websocket closed")
            break
    


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
        try:
            print("Loading agent", agent_name)
            class_name = agent_settings.pop("class")
            # class name is e.g. minichain.agents.programmer.Programmer
            # import the agent class
            module_name, class_name = class_name.rsplit(".", 1)
            module = __import__(module_name, fromlist=[class_name])
            agent_class = getattr(module, class_name)
            # create the agent
            print("Creating agent", agent_name, agent_class, agent_settings)
            agent = agent_class(**agent_settings.get("init", {}))
            # add the agent to the agents dict
            agents[agent_name] = agent
        except Exception as e:
            print("Error loading agent", agent_name, e)

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
