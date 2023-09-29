import json
import traceback

from pydantic import BaseModel

from minichain.utils.cached_openai import get_openai_response_stream
from minichain.dtypes import (
    SystemMessage,
    UserMessage,
    Cancelled,
)
from minichain.functions import Function, tool
from minichain.streaming import Stream
from minichain.schemas import DefaultResponse


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
    
    def initialize_session(self, history=[]):
        agent_session = Session(
            self,
            history=self.init_history + history,
        )
        return agent_session

    async def run(self, history=[], **arguments):
        """arguments: dict with values mentioned in the prompt template
        history: list of Message objects that are already part of the conversation, for follow up conversations
        """
        agent_session = self.initialize_session(history=history)
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


class Session():
    """
    - handle streaming
    - stateful history
    """
    def __init__(self, agent, history=[]):
        self.agent = agent
        self.history = history.copy()

    async def run_until_done(self):
        with self.agent.stream.conversation() as stream:
            await self.send_initial_messages(stream)
            while True:
                action = await self.get_next_action(stream)
                if action is not None:
                    output = await self.execute_action(action, stream)
                    if action.name == "return" and output is not False:
                        return output
    
    async def get_next_action(self, stream):
        # do the openai call
        # history = await get_summarized_history(self.history, self.agent.functions_openai)
        history = self.history
        # TODO
        with await stream.to(history, role="assistant") as stream:
            await get_openai_response_stream(
                history, self.agent.functions_openai, model=self.agent.llm, stream=stream
            )
        return history[-1].function_call

    async def execute_action(self, action, stream):
        with await stream.to(self.history, role="function", name=action.name) as stream:
            try:
                for function in self.agent.functions:
                    if function.name == action.name:
                        function.register_stream(stream)
                        function_output = await function(**action.arguments)
                        return function_output
                await stream.set(
                        f"Error: this function does not exist", action.name,
                    )
            except Exception as e:
                await stream.chunk(self.format_error_message(e))
        return False
    
    def format_error_message(self, e):
        if isinstance(e, Cancelled):
            raise e
        traceback.print_exc()
        try:
            msg = f"{type(e)}: {e} - {e.msg}"
        except AttributeError:
            msg = f"{type(e)}: {e}"
        msg = msg.replace("<class 'pydantic.error_wrappers.ValidationError'>", "Response could not be parsed, did you mean to call return?\nError:")
        msg = '```\n' + msg + '\n```'
        return msg

    async def follow_up(self, user_message):
        with await self.agent.stream.to(self.history, role="user") as stream:
            await stream.set(user_message.content)
        return await self.run_until_done()
    
    async def send_initial_messages(self, stream):
        for message in self.history:
            await stream.send(message)



