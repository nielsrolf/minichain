import inspect
import json
import traceback
import uuid
from dataclasses import asdict, dataclass
from pprint import pprint
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, create_model

from minichain.utils.cached_openai import get_openai_response_stream
from minichain.utils.debug import debug


@dataclass
class SystemMessage:
    content: str
    role: str = "system"
    conversation_id: str = None

    # short uuid as default
    id: Optional[str] = None

    def __post_init__(self):
        if self.id is None:
            self.id = str(uuid.uuid4().hex[:5])

    def dict(self):
        json = asdict(self)
        return json

    def __str__(self):
        return f"{self.role}: {self.content}"


@dataclass
class UserMessage:
    content: str
    role: str = "user"
    conversation_id: str = None

    # short uuid as default
    id: Optional[str] = None

    def __post_init__(self):
        if self.id is None:
            self.id = str(uuid.uuid4().hex[:5])

    def dict(self):
        json = asdict(self)
        return json

    def __str__(self):
        return f"{self.role}: {self.content}"


@dataclass
class FunctionCall:
    name: str
    arguments: Dict[str, Any]

    def dict(self):
        return asdict(self)


@dataclass
class AssistantMessage:
    content: str
    function_call: Optional[FunctionCall] = None
    role: str = "assistant"
    conversation_id: str = None
    # short uuid as default
    id: Optional[str] = None

    def __post_init__(self):
        if self.id is None:
            self.id = str(uuid.uuid4().hex[:5])

    def dict(self):
        json = asdict(self)
        return json

    def __str__(self):
        return f"{self.role}: {self.content} {self.function_call}"


@dataclass
class FunctionMessage:
    content: str
    name: str
    role: str = "function"
    conversation_id: str = None

    # short uuid as default
    id: Optional[str] = None

    def __post_init__(self):
        if self.id is None:
            self.id = str(uuid.uuid4().hex[:5])

    def dict(self):
        json = asdict(self)
        return json

    def __str__(self):
        return f"{self.name}: {self.content}"


def make_return_function(openapi_json: BaseModel):
    async def return_function(**arguments):
        return arguments

    function_obj = Function(
        name="return",
        function=return_function,
        openapi=openapi_json,
        description="End the conversation and return a structured response.",
    )
    return function_obj


class Agent:
    def __init__(
        self,
        functions,
        system_message,
        prompt_template="{task}".format,
        response_openapi=None,
        init_history=None,
        on_message_send=None,
        keep_first_messages=1,
        keep_last_messages=20,
        silent=False,
        keep_session=False,
        name=None,
        conversation_id=None,
    ):
        functions = functions.copy()
        self.response_openapi = response_openapi
        self.has_structured_response = response_openapi is not None
        if response_openapi is not None and not any(
            [i.name == "return" for i in functions]
        ):
            functions.append(make_return_function(response_openapi))
        self.functions = functions
        self.init_history = init_history
        self.system_message = system_message
        self.history = [system_message] + (init_history or [])
        self.prompt_template = prompt_template
        self.keep_first_messages = keep_first_messages
        self.keep_last_messages = keep_last_messages
        self.silent = silent
        self.keep_session = keep_session
        self.name = name or self.__class__.__name__

        async def do_nothing(*args, **kwargs):
            pass

        default_message_action = self.print_message if not silent else do_nothing
        self.on_message_send = on_message_send or default_message_action

        self.functions_openai = [i.openapi_json for i in self.functions]
        self.conversation_id = conversation_id or str(uuid.uuid4().hex[:5])

    async def print_message(self, message):
        print("-" * 120)
        print(f"Message to Agent({self.system_message.content})")
        if isinstance(message, dict):
            print(message)
            return
        print(message.role)
        print(message.content)
        try:
            pprint(message.function_call)
        except:
            pass
        print("-" * 120)
        # if input("Press enter to continue, or b to breakpoint") == "b":
        #     breakpoint()

    async def history_append(self, message):
        print("history append", message)
        message.conversation_id = self.conversation_id
        await self.on_message_send(message)
        self.history.append(message)

    def stream_to_history(self):
        streaming_message = AssistantMessage(
            "",
            conversation_id=self.conversation_id,
        )
        self.history.append(streaming_message)

        async def on_stream_message(message):
            streaming_message.content = message["content"]
            streaming_message.function_call = message.get("function_call", None)
            await self.on_message_send(streaming_message)

        return on_stream_message

    def stream_function_result(self, function_name):
        streaming_message = FunctionMessage(
            "", conversation_id=self.conversation_id, name=function_name
        )
        self.history.append(streaming_message)

        async def on_newline(newline, final=False):
            print("stream", self.__class__.__name__, newline)
            if not final:
                streaming_message.content += newline
            else:
                streaming_message.content = newline
            await self.on_message_send(streaming_message)

        on_newline.__name__ = f"stream_{function_name}_to_{self.conversation_id}"
        return on_newline

    async def run(self, keep_session=False, history=[], conversation_id=None, **arguments):
        """arguments: dict with values mentioned in the prompt template
        history: list of Message objects that are already part of the conversation, for follow up conversations
        """
        is_followup = len(history) > 0
        print("is_followup", is_followup, conversation_id, history)
        agent_session = Agent(
            self.functions,
            self.system_message,
            self.prompt_template,
            self.response_openapi,
            self.init_history,
            self.on_message_send,
            keep_first_messages=self.keep_first_messages,
            keep_last_messages=self.keep_last_messages,
            silent=self.silent,
            keep_session=keep_session,
            name=self.name,
            conversation_id=conversation_id if is_followup else None,
        )
        if not is_followup:
            await agent_session.send_initial_messages()
        else:
            # The history messages already have a message id and don't need to be sent again
            agent_session.history += history
        await agent_session.task_to_history(arguments)
        response = await agent_session.run_until_done()
        return response

    async def send_initial_messages(self):
        # Get the class name of the agent, but the child class name if this is a child class
        class_name = self.name or self.__class__.__name__
        await self.on_message_send(
            {
                "type": "start",
                "conversation_id": self.conversation_id,
                "agent": class_name
            }
        )
        self.system_message.conversation_id = self.conversation_id
        system_msg_dict = self.system_message.dict()
        system_msg_dict['is_init'] = True
        await self.on_message_send(system_msg_dict)
        for i in self.init_history or []:
            i.conversation_id = self.conversation_id
            i = i.dict()
            i['is_init'] = True
            await self.on_message_send(i)

    async def run_until_done(self):
        while True:
            assistant_message = await self.get_next_action()
            # await self.history_append(assistant_message)
            # Check if we are done and should return content
            if (
                not self.has_structured_response
                and assistant_message.content is not None
            ):
                await self.on_message_send(
                    {"type": "end", "conversation_id": self.conversation_id}
                )
                if not self.keep_session:
                    return assistant_message.content
                else:
                    self.init_history = self.history
                    return assistant_message.content, self
            elif (
                self.has_structured_response and assistant_message.function_call is None
            ):
                # We simulate a return function call that will probably fail and hint GPT to correct it
                assistant_message.function_call = FunctionCall(
                    name="return",
                    arguments=json.dumps({"content": assistant_message.content}),
                )
            function_call = assistant_message.function_call
            if function_call is not None:
                output = await self.execute_action(function_call)
                if function_call.name == "return" and output is not False:
                    if output is False:
                        breakpoint()
                    if self.keep_session:
                        output["session"] = self
                        self.init_history = self.history
                    await self.on_message_send(
                        {"type": "end", "conversation_id": self.conversation_id}
                    )
                    return output

    async def task_to_history(self, arguments):
        await self.history_append(UserMessage(self.prompt_template(**arguments)))

    async def get_next_action(self):
        # do the openai call
        indizes = list(range(len(self.history)))
        keep = (
            [indizes[0]]
            + indizes[1 : self.keep_first_messages + 1]
            + indizes[-self.keep_last_messages :]
        )
        keep = sorted(list(set(keep)))
        history = []
        for i in keep:
            msg = self.history[i].dict()
            msg.pop("conversation_id", None)
            msg.pop("id", None)
            history.append(msg)
        response = await get_openai_response_stream(
            history, self.functions_openai, stream=self.stream_to_history()
        )
        print(response)
        function_call = response.get("function_call", None)
        if function_call is not None:
            function_call = FunctionCall(**function_call)
        return AssistantMessage(
            response.get("content", None), function_call=function_call
        )

    # @debug
    async def execute_action(self, function_call):
        try:
            for function in self.functions:
                if function.name == function_call.name:
                    if function_call.name == "python":
                        # Somehow with python we get a string instead of a dict, which is probably easier for the model to handle, so we support it
                        try:
                            arguments = json.loads(function_call.arguments)
                        except:
                            arguments = {"code": function_call.arguments}
                    else:
                        arguments = json.loads(function_call.arguments)
                    function._register_stream(
                        self.stream_function_result(function.name)
                    )
                    function_output = await function(**arguments)
                    if not function.has_stream:
                        function_output_str = function_output
                        if not isinstance(function_output, str):
                            function_output_str = json.dumps(function_output)
                        function_message = FunctionMessage(
                            function_output_str, function.name
                        )
                        await self.history_append(function_message)
                    return function_output
            await self.history_append(
                FunctionMessage(
                    f"Error: this function does not exist", function_call.name
                )
            )
        except Exception as e:
            try:
                msg = f"{type(e)}: {e} - {e.msg}"
            except AttributeError:
                msg = f"{type(e)}: {e}"
            if not self.silent:
                traceback.print_exc()
                # breakpoint()

            await self.history_append(FunctionMessage(msg, function.name))
        # self.on_message_send(self.history[-1])
        print(self.history[-1].content)
        return False

    async def follow_up(self, user_message):
        await self.history_append(user_message)
        # self.on_message_send(self.history[-1])
        return await self.run_until_done()

    def as_function(self, name, description, prompt_openapi):
        def function(**arguments):
            return self.run(**arguments)

        function_tool = Function(
            prompt_openapi,
            name,
            function,
            description,
        )
        return function_tool


class Function:
    def __init__(self, openapi, name, function, description):
        """
        Arguments:
            openapi (dict): the openapi.json describing the function
            name (str): the name of the function
            function (any -> FunctionMessage): the function to call. Must return a FunctionMessage
            description (str): the description of the function
        """
        self.pydantic_model = None
        try:
            if isinstance(openapi, dict):
                parameters_openapi = openapi
            elif issubclass(openapi, BaseModel):
                parameters_openapi = openapi.schema()
                self.pydantic_model = openapi
            else:
                raise ValueError(
                    "openapi must be a dict or a pydantic BaseModel describing the function parameters."
                )
        except:
            print(openapi, type(openapi))
            breakpoint()
        self.parameters_openapi = parameters_openapi
        self.name = name
        self.function = function
        self.description = description
        self.has_stream = False

    async def __call__(self, **arguments):
        """Call the function with the given arguments.
        _stream: a function that is expected to be called with new parts of the output of the function string
                (e.g. new lines of a bash command)
        """
        if self.pydantic_model is not None:
            arguments = self.pydantic_model(**arguments).dict()
        response = await self.function(**arguments)
        print("response", response)
        return response

    def _register_stream(self, stream):
        self.stream = stream

    @property
    def openapi_json(self):
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters_openapi,
        }


def tool(name=None, description=None, **kwargs):
    """A decorator for tools.
    Example:

    @tool()
    def my_tool(some_input: str = Field(..., description="Some input.")):
        return output
    """

    def wrapper(f):
        # Get the function's arguments
        argspec = inspect.getfullargspec(f)

        def f_with_args(**inner_kwargs):
            # merge the arguments from the decorator with the arguments from the function
            merged = {**kwargs, **inner_kwargs}
            return f(**merged)

        # Create a Pydantic model from the function's arguments
        fields = {
            arg: (argspec.annotations[arg], Field(..., description=field.description))
            for arg, field in zip(argspec.args, argspec.defaults)
            if not arg in kwargs.keys()
        }

        pydantic_model = create_model(f.__name__, **fields)
        function = Function(
            name=name or f.__name__,
            description=description or f.__doc__,
            openapi=pydantic_model,
            function=f_with_args,
        )
        return function

    return wrapper


class Done(BaseModel):
    success: bool = Field(
        ...,
        description="Always set this to true to indicate that you are done with this function.",
    )
