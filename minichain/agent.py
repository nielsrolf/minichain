import openai
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional, Union
from minichain.utils.cached_openai import get_openai_response


@dataclass
class SystemMessage():
    content: str
    role: str = "system"

    def dict(self):
        return asdict(self)


@dataclass
class UserMessage():
    content: str
    role: str = "user"
    parent: Union["UserMessage", "SystemMessage", "AssistantMessage", "FunctionMessage"] = None

    def dict(self):
        return asdict(self)


@dataclass
class FunctionCall():
    name: str
    inputs: Dict[str, Any]

    def dict(self):
        return asdict(self)


@dataclass
class AssistantMessage():
    content: str
    function_call: Optional[FunctionCall] = None
    role: str = "assistant"
    parent: Union["UserMessage", "SystemMessage", "AssistantMessage", "FunctionMessage"] = None

    def dict(self):
        return asdict(self)


@dataclass
class FunctionMessage():
    content: str
    name: str
    role: str = "function"
    parent: Optional[AssistantMessage] = None

    def dict(self):
        return asdict(self)


class Agent():
    def __init__(self, functions, system_message, prompt_template="{task}".format, init_history=None, onUserMessage=None, onFunctionMessage=None, onAssistantMessage=None):
        self.functions = functions
        self.init_history = init_history
        self.system_message = system_message
        self.history = [system_message] + (init_history or [])
        self.prompt_template = prompt_template
        def do_nothing(*args, **kwargs):
            pass
        self.onUserMessage = onUserMessage or do_nothing
        self.onFunctionMessage = onFunctionMessage or do_nothing
        self.onAssistantMessage = onAssistantMessage or do_nothing
    

    
    def history_append(self, message):
        message.parent = self.history[-1]
        self.history.append(message)
    
    def run(self, **inputs):
        """inputs: dict with values mentioned in the prompt template"""
        agent_session = Agent(self.functions, self.system_message, self.prompt_template, self.init_history, onUserMessage=self.onUserMessage, onFunctionMessage=self.onFunctionMessage, onAssistantMessage=self.onAssistantMessage)
        agent_session.task_to_history(inputs)
        return agent_session.run_until_done()
    
    def run_until_done(self):
        while True:
            assistant_message = self.get_next_action()
            self.history_append(assistant_message)
            self.onAssistantMessage(self.history[-1])
            if assistant_message.content is not None:
                return assistant_message
            self.execute_action(assistant_message.function_call)
    
    def task_to_history(self, inputs):
        self.history_append(UserMessage(self.prompt_template(**inputs)))
        self.onUserMessage(self.history[-1])
    
    def get_next_action(self):
        # do the openai call
        response = get_openai_response(self.history, self.functions)
        return AssistantMessage(response['content'], response.get('function_call', None))
    
    def execute_action(self, function_call):
        if function_call["name"] == "done":
            return True
        for function in self.functions:
            if function.name == function_call["name"]:
                output = function(**function_call["inputs"])
                function_message = FunctionMessage(output, function.name)
                self.history_append(function_message)
                self.onFunctionMessage(self.history[-1])
                return False
            self.history_append(FunctionMessage("Error: this function does not exist", function.name))
            self.onFunctionMessage(self.history[-1])
            return False
    
    def follow_up(self, user_message):
        self.history_append(user_message)
        self.onUserMessage(self.history[-1])
        return self.run_until_done()

            
        


        

class Function():
    def __init__(self, openapi, name, function, description):
        self.openapi = openapi
        self.name = name
        self.function = function
        self.description = description
    
    def __call__(self, **inputs):
        return self.function(**inputs).content



