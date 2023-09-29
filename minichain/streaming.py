from minichain.dtypes import message_types
from uuid import uuid4


async def do_nothing(*args, **kwargs):
    pass


async def print_message(message):
    print(message)


prev_chunk_id = None
async def print_chunk(chunk, key, message_id):
    global prev_chunk_id
    chunk_id = f"{message_id}[{key}]"
    if chunk_id != prev_chunk_id:
        print(chunk_id, end=" ")
    prev_chunk_id = chunk_id
    print(chunk, end="")


class Stream:
    """
    Stream that keeps track of the streaming target and conversation id.

    Example:
        stream = Stream(to_websocket)
        with stream.conversation("123") as stream
            history = []
            with stream.to(history, type=AssistantMessage) as stream:
                stream.chunk("Hello", key="content")
                stream.chunk("World", key="content")
                print(history)
                Out:
                [{"content": "Hello World", conversation_id: "123", id: 1}]
            stream.set("Override", key="content")
            print(history)
                Out:
                [{"content": "Override", conversation_id: "123", id: 1}]
        with stream.to(history, type=FunctionMessage) as stream:
            function.stream = stream
            function()
                stream.chunk("hello")
                stream.chunk("world")
            print(history)
                Out:
                [{"content": "Override", conversation_id: "123", id: 1}, {"content": "hello world", conversation_id: "123", id: 2}]
    """
    def __init__(self, on_message=print_message, conversation_stack=[], current_message=None, on_chunk=print_chunk, history=None):
        if on_message is None:
            on_message = do_nothing
        self.on_message = on_message
        self.on_chunk = on_chunk
        self.conversation_stack = conversation_stack
        self.current_message = current_message or {"id": "hidden", "role": "hidden", "conversation_id": "hidden"}
        self.history = history or []
    
    def __enter__(self):
        return self
    
    def __exit__(self, type, value, traceback):
        print("exit with", self.current_message)
        if self.current_message["role"] != "hidden":
            role = self.current_message["role"]
            message_type = message_types[role]
            self.history.append(message_type(**self.current_message))
    
    def conversation(self, conversation_id=None):
        if conversation_id is None:
            conversation_id = str(uuid4().hex[:5])
        conversation_stack = self.conversation_stack 
        if self.current_message is not None:
            try:
                conversation_stack += [self.current_message["id"]]
            except:
                breakpoint()
        conversation_stack += [conversation_id]
        return Stream(self.on_message, conversation_stack, None, self.on_chunk)
    
    def to(self, history, role):
        message_type = message_types[role]
        current_message = message_type(content="", conversation_id=self.conversation_stack[-1]).dict()
        message_stream = Stream(self.on_message, self.conversation_stack, current_message, self.on_chunk, history)
        return message_stream
        
    async def chunk(self, diff, key):
        """for nested keys: key='content.nested_key'"""
        nested("add", self.current_message, key, diff)
        if self.on_chunk:
            await self.on_chunk(diff, key, self.current_message['id'])
        else:
            await self.on_message(self.current_message)
    
    async def chunk_dict(self, data, key=""):
        for k, v in data.items():
            if k == 'role':
                continue
            if isinstance(v, dict):
                await self.chunk_dict(v, key=f"{key}.{k}")
            else:
                full_key = f"{key}.{k}"
                if full_key.startswith("."):
                    full_key = full_key[1:]
                await self.chunk(v, full_key)
    
    async def set(self, value, key=None):
        """override the current message with a new one, optionally with a nested key
        
        Arguments:
            value: (dict | Message)
                - if message:
                    get dict from message, delete id fields
                - if dict:
                    - if key is not None: override the value at key
                    - if key is None: override the entire message
        """
        if not isinstance(value, dict):
            value = value.dict()
            value = {k: v for k, v in value.items() if "id" not in k}
        if key is None:
            for k, v in self.current_message.items():
                if "id" in k or k == 'role':
                    value[k] = v
            self.current_message = value
        else:
            nested("add", self.current_message, key, value)
        
        await self.on_message(self.current_message)
    
    async def send(self, message):
        await self.on_message(message.dict())
    
    async def __call__(self, chunk, key='content'):
        """prepare to be used by a function with no surrounding conversation"""
        if self.current_message is None:
            self.current_message = {}
        if "id" not in self.current_message:
            self.current_message["id"] = "hidden"
        if self.current_message is not None:
            await self.chunk(chunk, key)
    
    def silent(self):
        return Stream(do_nothing, self.conversation_stack, None, do_nothing)
       

def nested(mode, dictionary, key, value):
    try:
        keys = key.split(".")
        for i in keys[:-1]:
            if i not in dictionary:
                dictionary[i] = {}
            dictionary = dictionary[i]
        if mode == "add":
            current = ""
            if keys[-1] in dictionary:
                current = dictionary[keys[-1]]
            dictionary[keys[-1]] = current + (value or "")
        elif mode == "set":
            dictionary[keys[-1]] = value
    except Exception as e:
        print(e)
        breakpoint()


class APIStream(Stream):
    async def enter_conversation(self, conversation_id):
        await self.on_message({"conversation_id": conversation_id, "type": "start"})
    
    async def exit_conversation(self, conversation_id):
        await self.on_message({"conversation_id": conversation_id, "type": "end"})

