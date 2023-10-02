from minichain.dtypes import message_types
from uuid import uuid4


async def do_nothing(*args, **kwargs):
    pass


async def print_message(message):
    print(message)


prev_chunk_id = None
async def print_chunk(diff, message_id, _recursive_key=None):
    global prev_chunk_id
    if isinstance(diff, dict):
        for key, value in diff.items():
            await print_chunk(value, message_id, key)
        return
    chunk_id = f"{message_id}[{_recursive_key}]"
    if chunk_id != prev_chunk_id:
        print(chunk_id, end=" ")
    prev_chunk_id = chunk_id
    print(diff, end="")


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
    def __init__(self, on_message=print_message, conversation_stack=[], current_message=None, on_chunk=print_chunk, history=None, agent=None):
        if on_message is None:
            on_message = do_nothing
        self.on_message = on_message
        self.on_chunk = on_chunk
        # remove duplicate entries from stack but keep the order
        self.conversation_stack = [i for n, i in enumerate(conversation_stack) if i not in conversation_stack[:n]]

        self.current_message = current_message or {"id": "hidden", "role": "hidden", "conversation_id": "hidden"}
        self.history = history or []
        self.originally_streamed = {}
        self.agent = agent

        self.logs = []
    
    def __enter__(self):
        return self
    
    def __exit__(self, type, value, traceback):
        if self.current_message["role"] != "hidden":
            role = self.current_message["role"]
            message_type = message_types[role]
            self.history.append(message_type(**self.current_message))
    
    async def conversation(self, conversation_id=None, agent=None):
        if conversation_id is None:
            conversation_id = str(uuid4().hex[:5])
        conversation_stack = self.conversation_stack
        if self.current_message["id"] != "hidden":
            conversation_stack += [self.current_message["id"]]
        conversation_stack += [conversation_id]
        stream = self.__class__(
            on_message=self.on_message,
            conversation_stack=conversation_stack,
            current_message=None,
            on_chunk=self.on_chunk,
            agent=agent
        )
        await stream.send_stack()
        return stream
    
    async def to(self, history, role, **kwargs):
        """
        This method must be called before sending data to the stream.
        It creates the id for the new conversation, updates the conversation stack, and returns a stream that can send data
        """
        message_type = message_types[role]
        try:
            conv_id = self.conversation_stack[-1]
            if self.current_message["id"] != "hidden":
                conv_id = self.current_message["id"]
            current_message = message_type(content="", conversation_id=conv_id, **kwargs).dict()
        except Exception as e:
            print(e)
            print(role, kwargs)
            breakpoint()
            raise e
        # # send the conversation stack update
        # stack_msg = {"type": "stack", "stack": self.conversation_stack + [current_message["id"]]}
        # await self.on_message(stack_msg)

        message_stream = self.__class__(
            on_message=self.on_message,
            conversation_stack=self.conversation_stack + [current_message["id"]],
            current_message=current_message,
            on_chunk=self.on_chunk,
            history=history,
            agent=self.agent
        )
        # set initial msg
        await message_stream.send_stack()
        await message_stream.set(current_message)
        message_stream.originally_streamed = dict(current_message)
        return message_stream
    
    async def send_stack(self):
        stack_msg = {"type": "stack", "stack": self.conversation_stack, "agent": self.agent}
        await self.on_message(stack_msg)
        
    async def chunk(self, diff):
        """diff: eg
            - {function_call: {arguments: {commands: ["echo"]}}}
            - {function_call: {arguments: {commands: [" world"]}}}
        """
        if isinstance(diff, str):
            diff = {"content": diff}
        print("not streaming diffs in: ", self.originally_streamed)
        for initially_streamed, value in self.originally_streamed.items():
            if value is not None and value != "":
                diff.pop(initially_streamed, None)
        print("add", diff, "to", self.current_message)
        nested("add", self.current_message, diff)
        print(self.current_message['role'])
        self.logs.append({"diff": diff, "message": self.current_message})
        if self.on_chunk:
            await self.on_chunk(diff, self.current_message['id'])
        else:
            await self.on_message(self.current_message)
    
    async def set(self, value):
        """override the current message with a new one, optionally with a nested key
        
        Arguments:
            value: (dict | Message)
                - if string: treat as {"content": value}
                - if message:
                    get dict from message, delete id fields
                - if dict:
                    - if key is not None: override the value at key
                    - if key is None: override the entire message
        """
        if isinstance(value, str):
            value = {"content": value}
        self.logs.append({"value": value, "message": self.current_message})
        if not isinstance(value, dict):
            value = value.dict()
            value = {k: v for k, v in value.items() if "id" not in k}
        nested("set", self.current_message, value)
        await self.on_message(self.current_message)
    
    async def send(self, message):
        """send a complete message to the stream in one go"""
        if not isinstance(message, dict):
            message = message.dict()
        stack_msg = {"type": "stack", "stack": self.conversation_stack + [message["id"]]}
        await self.on_message(stack_msg)
        await self.on_message(message)
    
    async def __call__(self, chunk):
        """prepare to be used by a function with no surrounding conversation"""
        await self.chunk(chunk)
    
    def silent(self):
        return Stream(do_nothing, self.conversation_stack, None, do_nothing)
       

def nested(mode, dictionary, value):
    if not isinstance(value, dict):
        if dictionary is None and value is None:
            return None
        if dictionary is None and isinstance(value, str):
            dictionary = ""
        if mode == "add":
            return dictionary + (value or "")
        elif mode == "set":
            return value
    if dictionary is None:
        dictionary = {}
    for k, v in value.items():
        dictionary[k] = nested(mode, dictionary.get(k, None), v)
    return dictionary
