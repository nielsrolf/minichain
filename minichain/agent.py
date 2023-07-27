import dataclasses
import inspect
import json
from dataclasses import asdict, dataclass
from pprint import pprint
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, create_model

from minichain.utils.cached_openai import get_openai_response
from minichain.utils.debug import debug


@dataclass
class SystemMessage:
    content: str
    role: str = "system"

    def dict(self):
        return asdict(self)

    def __str__(self):
        return f"{self.role}: {self.content}"


@dataclass
class UserMessage:
    content: str
    role: str = "user"
    parent: Union[
        "UserMessage", "SystemMessage", "AssistantMessage", "FunctionMessage"
    ] = None

    def dict(self):
        return asdict(self)

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
    parent: Union[
        "UserMessage", "SystemMessage", "AssistantMessage", "FunctionMessage"
    ] = None

    def dict(self):
        return asdict(self)

    def __str__(self):
        return f"{self.role}: {self.content} {self.function_call}"


@dataclass
class FunctionMessage:
    content: str
    name: str
    role: str = "function"
    parent: Optional[AssistantMessage] = None

    def dict(self):
        return asdict(self)


def make_return_function(openapi_json: BaseModel):
    def return_function(**arguments):
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
        on_user_message=None,
        on_function_message=None,
        on_assistant_message=None,
        function_stream=None,
        assistant_stream=None,
        keep_first_messages=1,
        keep_last_messages=20,
        silent=False,
        keep_session=False,
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

        def do_nothing(*args, **kwargs):
            pass

        default_message_action = self.print_message if not silent else do_nothing
        self.on_user_message = on_user_message or default_message_action
        self.on_function_message = on_function_message or default_message_action
        self.on_assistant_message = on_assistant_message or default_message_action

        self.function_stream = function_stream or do_nothing
        self.assistant_stream = assistant_stream or do_nothing

        self.functions_openai = [i.openapi_json for i in self.functions]
        for function in self.functions:
            function._register_stream(self.function_stream)

    def print_message(self, message):
        print("-" * 120)
        print(f"Message to Agent({self.system_message.content})")
        print(message.role)
        print(message.content)
        try:
            pprint(message.function_call)
        except:
            pass
        print("-" * 120)
        # if input("Press enter to continue, or b to breakpoint") == "b":
        #     breakpoint()

    def history_append(self, message):
        message.parent = self.history[-1]
        self.history.append(message)

    def run(self, keep_session=False, **arguments):
        """arguments: dict with values mentioned in the prompt template"""
        agent_session = Agent(
            self.functions,
            self.system_message,
            self.prompt_template,
            self.response_openapi,
            self.init_history,
            on_user_message=self.on_user_message,
            on_function_message=self.on_function_message,
            on_assistant_message=self.on_assistant_message,
            keep_first_messages=self.keep_first_messages,
            keep_last_messages=self.keep_last_messages,
            silent=self.silent,
            keep_session=keep_session,
        )
        agent_session.task_to_history(arguments)
        return agent_session.run_until_done()

    def run_until_done(self):
        while True:
            assistant_message = self.get_next_action()
            self.history_append(assistant_message)
            self.on_assistant_message(self.history[-1])
            # Check if we are done and should return content
            if (
                not self.has_structured_response
                and assistant_message.content is not None
            ):
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
                output = self.execute_action(function_call)
                if function_call.name == "return" and output is not False:
                    if output is False:
                        breakpoint()
                    if self.keep_session:
                        output["session"] = self
                        self.init_history = self.history
                    return output

    def task_to_history(self, arguments):
        self.history_append(UserMessage(self.prompt_template(**arguments)))
        self.on_user_message(self.history[-1])

    def get_next_action(self):
        # do the openai call
        indizes = list(range(len(self.history)))
        keep = (
            [indizes[0]]
            + indizes[1 : self.keep_first_messages + 1]
            + indizes[-self.keep_last_messages :]
        )
        keep = sorted(list(set(keep)))
        history = [self.history[i] for i in keep]
        response = get_openai_response(history, self.functions_openai)
        function_call = response.get("function_call", None)
        if function_call is not None:
            function_call = FunctionCall(**function_call)
        return AssistantMessage(
            response.get("content", None), function_call=function_call
        )

    
    def execute_action(self, function_call):
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
                    function_output = function(**arguments)
                    function_output_str = function_output
                    if not isinstance(function_output, str):
                        function_output_str = json.dumps([dataclasses.asdict(i) for i in function_output])
                    function_message = FunctionMessage(
                        function_output_str, function.name
                    )
                    self.history_append(function_message)
                    self.on_function_message(self.history[-1])
                    return function_output
            self.history_append(
                FunctionMessage(
                    f"Error: this function does not exist", function_call.name
                )
            )
        except Exception as e:
            raise e
            try:
                msg = f"{type(e)}: {e} - {e.msg}"
            except AttributeError:
                msg = f"{type(e)}: {e}"
            if not self.silent:
                breakpoint()
            self.history_append(FunctionMessage(msg, function.name))
        self.on_function_message(self.history[-1])
        print(self.history[-1].content)
        return False

    def follow_up(self, user_message):
        self.history_append(user_message)
        self.on_user_message(self.history[-1])
        return self.run_until_done()

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

    def __call__(self, **arguments):
        if self.pydantic_model is not None:
            arguments = self.pydantic_model(**arguments).dict()
        return self.function(**arguments)

    def _register_stream(self, stream):
        self.stream = stream

    @property
    def openapi_json(self):
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters_openapi,
        }


def tool(name=None, description=None):
    """A decorator for tools.
    Example:

    @tool()
    def my_tool(some_input: str = Field(..., description="Some input.")):
        return output
    """

    def wrapper(f):
        # Get the function's arguments
        argspec = inspect.getfullargspec(f)

        # Create a Pydantic model from the function's arguments
        fields = {
            arg: (argspec.annotations[arg], Field(..., description=field.description))
            for arg, field in zip(argspec.args, argspec.defaults)
        }

        pydantic_model = create_model(f.__name__, **fields)
        function = Function(
            name=name or f.__name__,
            description= description or f.__doc__,
            openapi=pydantic_model,
            function=f,
        )
        return function

    return wrapper


class Done(BaseModel):
    success: bool = Field(
        ...,
        description="Always set this to true to indicate that you are done with this function.",
    )
