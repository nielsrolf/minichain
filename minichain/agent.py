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


class Cancelled(Exception):
    pass


def make_return_function(openapi_json: BaseModel, check=None):
    async def return_function(**arguments):
        if check is not None:
            check(**arguments)
        return arguments

    function_obj = Function(
        name="return",
        function=return_function,
        openapi=openapi_json,
        description="End the conversation and return a structured response.",
    )
    return function_obj


def parse_function_call(function_call: Optional[Dict[str, Any]]):
    if function_call is None:
        return None
    try:
        arguments = json.loads(function_call["arguments"])
        return FunctionCall(**function_call)
    except:
        pass
    if '"code": ```' in function_call["arguments"]:
        # replace first occurrence of ``` with " and last
        try:
            before, after = function_call["arguments"].split('"code": ```', 1)
            try:
                code, after = after.rsplit("```,", 1)[0]
            except:
                code, after = after.rsplit("```", 1)[0]
            arguments_no_code = json.loads(before + after)
            arguments = {"code": code, **arguments_no_code}
            function_call["arguments"] = json.dumps(arguments)
            return FunctionCall(**function_call)
        except Exception as e:
            print(e)
            breakpoint()
    
    if '"code": `' in function_call["arguments"]:
        try:
            # replace first occurrence of ``` with " and last
            before, after = function_call["arguments"].split('"code": `', 1)
            try:
                code, after = after.rsplit("`,", 1)[0]
            except:
                code, after = after.rsplit("`", 1)[0]
            arguments_no_code = json.loads(before + after)
            arguments = {"code": code, **arguments_no_code}
            function_call["arguments"] = json.dumps(arguments)
            return FunctionCall(**function_call)
        except Exception as e:
            print(e)
            breakpoint()
    return FunctionCall(**function_call)

import tiktoken


def count_tokens(text):
    encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
    num_tokens = len(encoding.encode(text))
    return num_tokens


history_summarize_prompt = (
    "Summarize the following message history:\n"
    "- each message is presented in the format: 'Message <id>: <message json>'\n"
    "- you are the assistant. Formulate the summaries in first person, e.g. 'I did this and that.'\n"
    "- your task is to construct a shorter version of the message history that contains all relevant information that is needed to complete the task\n"
    "- you must keep every system message (role: system)"
    "- summarize steps related to completed tasks, but mention the full paths to all files that were created or modified\n"
    "- don't shorten it too much - you will in the next step be asked to continue the task with only the information you are keeping now. Details especially in the code are important. For tasks that are completed, you can remove the messages but add a summary that lists all the file paths you (assistant) worked on. \n"
    "- keep in particular the last messages that contain relevant details about the next steps.\n"
    "- you should try to shorten the history by about 50% and reduce the number of messages by at least 1\n"
    "- end the history in a way that makes it very clear what should be done next, and make sure all the information needed to complete the task is there\n"
)
async def get_summarized_history(history, functions, max_tokens=6000):
    messages = [i.dict() for i in history]
    for i in messages:
        i.pop("id")
        i.pop("conversation_id")
    
    if messages[0]['content'] == history_summarize_prompt:
        # We are the summarizer, if we summarize at this point we go into an infinite loop
        return messages
    
    original_history = list(messages)
    print("original history", len(original_history))
    tokens = count_tokens(json.dumps(functions))
    assert tokens < max_tokens, f"Too many tokens in functions: {tokens} > {max_tokens}"
    # while the total token number is too large, we summarize the first max_token/2 messages and try again
    step = 1
    function_tokens = count_tokens(json.dumps(functions))
    while count_tokens(json.dumps(messages)) + function_tokens > max_tokens :
        print("TOKENS", count_tokens(json.dumps(messages)) + function_tokens, function_tokens, max_tokens)
        print("step", step)
        # Get as many messages as possible without exceeding the token limit. We first summarize only the first 75%, if that was not enough we summarize 87.5%, 93.75%, ...
        for i in range(1, len(messages)):
            if count_tokens(json.dumps(messages[:i])) > (max_tokens - function_tokens) * (1 - 0.5 ** (step + 1)):
                break
        step += 1
        # Try to summarize the chunk until we get a summary that is smaller than the chunk. If we fail, increase the chunk size and try again
        tokens_to_summarize = count_tokens(json.dumps(messages[:i]))
        summary = await summarize_chunk(messages[:i])
        summarized_tokens = count_tokens(json.dumps(summary))

        print("CHUNK TOKENS", tokens_to_summarize)
        print("MAYBE FAILED?", summarized_tokens, "/", tokens_to_summarize)
        if summarized_tokens > tokens_to_summarize:
            print("FAILED")
            breakpoint()
            continue # with increased step, and therefore larger chunk
        messages = summary + messages[i:]
    
    if messages[-1]["content"].startswith("(summarized)"):
        messages[-1]["content"] += "\n\nOkay let's continue with the task."

    with open(".minichain/last_summarized_history_final.json", "w") as f:
        json.dump({"original_history": original_history, "summarized_history": messages, "length_original": count_tokens(json.dumps(original_history)), "length_shortened": count_tokens(json.dumps(messages))}, f)
    
    return messages
        


class ReferencesToOriginalMessages(BaseModel):
    original_message_id: Optional[int] = Field(None, description="The id of the original message that you want to keep.")
    summary: Optional[str] = Field(None, description="A summary of one or more messages that you want to keep instead of the original message.")


class ShortenedHistory(BaseModel):
    messages: List[ReferencesToOriginalMessages] = Field(..., description="The messages you want to keep from the original history. You can either pass message ids - those messages will be kept and not summarized - or no id but a text summary to insert into the history.")


async def summarize_chunk(history):
    prompt = ""
    for i, message in enumerate(history):
        prompt += f"Message {i}: {json.dumps(message)}\n"
    
    example = FunctionCall(name="return", arguments=json.dumps({"messages": [{"original_message_id": 0}, {"summary": "This is a summary of messages 2-6"}, {"original_message_id": 7}]}))

    prompt += (
        "\n\nReturn the messages you want to keep with summaries for the less relevant messages by using the return function. Specify the shortened history like in this example:\n" +
        json.dumps(example.dict(), indent=2)
    )

    with open(".minichain/last_summarize_prompt", "w") as f:
        f.write(prompt)

    summarizer = Agent(
        functions=[],
        system_message=SystemMessage(history_summarize_prompt),
        prompt_template="{prompt}".format,
        response_openapi=ShortenedHistory,
    )

    summary = await summarizer.run(prompt=prompt)
    print(summary)

    new_history = []
    for keep in summary['messages']:
        if keep['original_message_id'] is not None:
            new_history.append(history[keep['original_message_id']])
        else:
            new_history.append({
                "role": "assistant",
                "content": f"(summarized):\n{keep['summary']}",
            })
    with open(".minichain/last_summary.json", "w") as f:
        json.dump({"history": history, "summary": summary, "new_histrory": new_history}, f)
    return new_history



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

        self.conversation_id = conversation_id or str(uuid.uuid4().hex[:5])

    @property
    def functions_openai(self):
        return [i.openapi_json for i in self.functions]

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
            if message is None:
                return
            streaming_message.content = message.get("content", "")
            streaming_message.function_call = parse_function_call(message.get("function_call", None))
            # TODO parse here: e.g. `fake JSON` -> JSON

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
            conversation_id=conversation_id,
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
        
        history = await get_summarized_history(self.history, self.functions_openai)
        response = await get_openai_response_stream(
            history, self.functions_openai, stream=self.stream_to_history()
        )
        return self.history[-1]
        # print(response)
        # function_call = response.get("function_call", None)
        # if function_call is not None:
        #     function_call = FunctionCall(**function_call)
        # return AssistantMessage(
        #     response.get("content", None), function_call=function_call
        # )

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
            # check if it's a pydantic validation error to guide gpt
            traceback.print_exc()
            if isinstance(e, Cancelled):
                raise e
            try:
                msg = f"{type(e)}: {e} - {e.msg}"
            except AttributeError:
                msg = f"{type(e)}: {e}"
            if not self.silent:
                traceback.print_exc()
                # breakpoint()
            msg = msg.replace("<class 'pydantic.error_wrappers.ValidationError'>", "Response could not be parsed, did you mean to call return?\nError:")

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
        function_tool.has_stream = True
        return function_tool

    def register_on_message_send(self, on_message_send):
        self.on_message_send = on_message_send
        for function in self.functions:
            function.register_on_message_send(on_message_send)


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
    
    # def parse(self, response):
    #     """This method is for child classes that want to add extra parsing logic to the response, e.g. python"""
    #     return response

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
        # return self.parse(response)

    def _register_stream(self, stream):
        self.stream = stream

    @property
    def openapi_json(self):
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters_openapi,
        }
    
    def register_on_message_send(self, on_message_send):
        """This is only relevant for agents used by the function. Other function result streams are
        registered just before the function is called."""
        for maybe_agent in self.__dict__.values():
            if isinstance(maybe_agent, Agent):
                maybe_agent.register_on_message_send(on_message_send)


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
