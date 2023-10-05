import json
import traceback

from pydantic import BaseModel
import pydantic.error_wrappers

from minichain.dtypes import (Cancelled, SystemMessage, UserMessage,
                              messages_types_to_history)
from minichain.functions import Function
from minichain.schemas import DefaultResponse
from minichain.streaming import Stream
from minichain.utils.cached_openai import get_openai_response_stream
from minichain.utils.summarize_history import get_summarized_history


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


class Agent:
    def __init__(
        self,
        functions,
        system_message,
        prompt_template="{task}".format,
        response_openapi=DefaultResponse,
        init_history=[],
        stream=None,
        name=None,
        llm="gpt-4-0613",
    ):
        functions = functions.copy()
        self.response_openapi = response_openapi
        self.has_structured_response = response_openapi is not None
        if response_openapi is not None and not any(
            [i.name == "return" for i in functions]
        ):
            functions.append(make_return_function(response_openapi))
        self.functions = functions
        system_message = SystemMessage(system_message)
        self.init_history = [system_message] + init_history
        self.prompt_template = prompt_template
        self.name = name or self.__class__.__name__
        self.llm = llm
        self.stream = stream or Stream()

    @property
    def functions_openai(self):
        return [i.openapi_json for i in self.functions]

    async def initialize_session(self, history=[]):
        agent_session = Session(
            self,
            history=self.init_history + history,
        )
        if len(history) == 0:
            # we are starting a new conversation
            agent_session.stream = await self.stream.conversation(agent=self.name)
        else:
            # we are following up on a conversation
            agent_session.stream = self.stream
        return agent_session

    async def run(self, history=[], **arguments):
        """arguments: dict with values mentioned in the prompt template
        history: list of Message objects that are already part of the conversation, for follow up conversations
        """
        agent_session = await self.initialize_session(history=history)
        agent_session.history.append(UserMessage(self.prompt_template(**arguments)))
        response = await agent_session.run_until_done()
        return response

    def register_stream(self, stream):
        self.stream = stream

    def as_function(self, name, description, prompt_openapi):
        def function(**arguments):
            return self.run(**arguments)

        function_tool = Function(
            prompt_openapi,
            name,
            function,
            description,
            stream=self.stream,
        )
        return function_tool


class Session:
    """
    - handle streaming
    - stateful history
    """

    def __init__(self, agent, history=[]):
        self.agent = agent
        self.history = history.copy()

    async def run_until_done(self):
        with self.stream as stream:
            await self.send_initial_messages(stream)
            while True:
                action = await self.get_next_action(stream)
                if action is not None:
                    output = await self.execute_action(action, stream)
                    if action.name == "return" and output is not False:
                        # output is the output of the return function
                        # since each function returns a string, we need to parse the output
                        return json.loads(output)

    async def get_next_action(self, stream):
        history_without_ids = messages_types_to_history(self.history)
        # summarized_history = await get_summarized_history(
        #     history_without_ids, self.agent.functions_openai
        # )
        summarized_history = history_without_ids
        # do the openai call
        with await stream.to(self.history, role="assistant") as stream:
            await get_openai_response_stream(
                summarized_history,
                self.agent.functions_openai,
                model=self.agent.llm,
                stream=stream,
            )
        return self.history[-1].function_call

    async def execute_action(self, action, stream):
        with await stream.to(self.history, role="function", name=action.name) as stream:
            try:
                for function in self.agent.functions:
                    if function.name == action.name:
                        function.register_stream(stream)
                        if not isinstance(action.arguments, dict):
                            await stream.set(
                                f"Error: arguments for {function.name} are not valid JSON."
                            )
                            return False
                        function_output = await function(**action.arguments)
                        return function_output
                await stream.set(
                    f"Error: this function does not exist. Available functions: {', '.join([i.name for i in self.agent.functions])}"
                )
            # catch pydantic validation errors
            except pydantic.error_wrappers.ValidationError as e:
                breakpoint()
                await stream.chunk(self.format_error_message(e))
            except TypeError as e:
                if "missing 1 required positional argument: 'code'" in str(e):
                    await stream.set(
                        f"Error: this function requires a code. Use the normal message content field to put  the code like here:\n```\ncode here\n```"
                    )
                else:
                    raise e
            except Exception as e:
                print(self.format_error_message(e))
                breakpoint()
                print()
        return False

    def format_error_message(self, e):
        if isinstance(e, Cancelled):
            raise e
        traceback.print_exc()
        try:
            msg = f"{type(e)}: {e} - {e.msg}"
        except AttributeError:
            msg = f"{type(e)}: {e}"
        msg = msg.replace(
            "<class 'pydantic.error_wrappers.ValidationError'>",
            "Response could not be parsed, did you mean to call return?\nError:",
        )
        msg = "```\n" + msg + "\n```"
        return msg

    async def follow_up(self, user_message):
        with await self.stream.to(self.history, role="user") as stream:
            await stream.set(user_message.content)
        return await self.run_until_done()

    async def send_initial_messages(self, stream):
        for message in self.history:
            await stream.send(message)

    def register_stream(self, stream):
        self.stream = stream
