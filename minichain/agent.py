import json

from pydantic import BaseModel

from minichain.dtypes import (SystemMessage, UserMessage, ExceptionForAgent,
                              AssistantMessage, FunctionMessage, messages_types_to_history)
from minichain.functions import Function
from minichain.schemas import DefaultResponse, DefaultQuery
from minichain.message_handler import MessageDB, Conversation
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
        message_handler=None,
        name=None,
        # llm="gpt-3.5-turbo",
        llm="gpt-4-0613",
    ):
        functions = functions.copy()
        self.response_openapi = response_openapi
        self.has_structured_response = response_openapi is not None
        if response_openapi is not None and not any(
            [i.name == "return" for i in functions]
        ):
            functions.append(make_return_function(response_openapi))
        self.system_message = system_message
        self.functions = functions
        self._init_history = init_history
        self.prompt_template = prompt_template
        self.name = name or self.__class__.__name__
        self.llm = llm
        self.message_handler = message_handler or MessageDB()
    
    @property
    def init_history(self):
        return [SystemMessage(self.system_message)] + self._init_history

    @property
    def functions_openai(self):
        return [i.openapi_json for i in self.functions]
    
    async def before_run(self, conversation=None, **arguments):
        """Hook for subclasses to run code before the run method is called."""
        pass

    async def session(self, conversation=None, **arguments):
        if not isinstance(conversation, Conversation):
            if conversation is None:
                conversation = await self.message_handler.conversation(meta=dict(agent=self.name))
            else:
                conversation = await conversation.conversation(meta=dict(agent=self.name))
            for message in self.init_history:
                await conversation.send(message, is_initial=True)
        agent_session = Session(self, conversation)
        await self.before_run(agent_session.conversation, **arguments)
        return agent_session

    async def run(self, conversation=None, message_meta=None, **arguments):
        """arguments: dict with values mentioned in the prompt template
        history: list of Message objects that are already part of the conversation, for follow up conversations
        """
        agent_session = await self.session(conversation, **arguments)
        message_meta = message_meta or {}
        await agent_session.conversation.send(
            UserMessage(self.prompt_template(**arguments)),
            is_initial=False,
            **message_meta
        )
        response = await agent_session.run_until_done()
        return response

    def register_message_handler(self, message_handler):
        self.message_handler = message_handler

    def as_function(self, name, description, prompt_openapi=DefaultQuery):
        async def function(**arguments):
            result = await self.run(**arguments)
            if len(result.keys()) == 1:
                return list(result.values())[0]
            return json.dumps(result)

        function_tool = Function(
            prompt_openapi,
            name,
            function,
            description,
            message_handler=self.message_handler,
        )
        # Make sure both the functions register_message_handler and the agent's register_message_handler are called
        function_tool.from_agent = self
        return function_tool
    
    async def before_return(self, output):
        """Hook for subclasses to run code before the return method is called."""
        pass


class Session:
    """
    - handle message_handlering
    - stateful history
    """

    def __init__(self, agent, conversation):
        self.agent = agent
        self.conversation = conversation
        self._force_call = None

    async def run_until_done(self):
        while True:
            action = await self.get_next_action()
            if action is not None and action.get('name') is not None:
                output = await self.execute_action(action)
                if action['name'] == "return" and output is not False:
                    # output is the output of the return function
                    # since each function returns a string, we need to parse the output
                    await self.agent.before_return(output)
                    print("output", output)
                    return json.loads(output)
            else:
                await self.conversation.send(
                    UserMessage("INFO: no action was taken. In order to end the conversation, please call the 'return' function. In order to continue, please call a function.")
                )

    async def get_next_action(self):
        history_without_ids = messages_types_to_history(self.conversation.messages)
        # summarized_history = await get_summarized_history(
        #     history_without_ids, self.agent.functions_openai
        # )
        summarized_history = history_without_ids
        # do the openai call
        async with self.conversation.to(AssistantMessage()) as message_handler:
            llm_response = await get_openai_response_stream(
                summarized_history,
                self.agent.functions_openai,
                model=self.agent.llm,
                stream=message_handler,
                force_call=self._force_call,
            )
        return llm_response.get('function_call')

    async def execute_action(self, action):
        async with self.conversation.to(FunctionMessage(name=action['name'])) as message_handler:
            if not isinstance(action['arguments'], dict):
                await message_handler.set(f"Error: arguments for {function.name} are not valid JSON.")
                return False
            
            found = False
            for function in self.agent.functions:
                if function.name == action['name']:
                    found = True
                    break
            
            if not found:
                await message_handler.set(
                    f"Error: this function does not exist. "
                    f"Available functions: {', '.join([i.name for i in self.agent.functions])}"
                )
                return False
            
            try:
                function.register_message_handler(message_handler)
                function_output = await function(**action['arguments'])
                self._force_call = None
                return function_output
            except ExceptionForAgent as e:
                error_msg = str(e)
                if action['name'] == "return":
                    self._force_call = action['name']
                await message_handler.set(error_msg)
                
        return False

    def register_message_handler(self, message_handler):
        self.message_handler = message_handler
