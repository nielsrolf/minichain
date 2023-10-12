from typing import Any, Dict, Optional


def SystemMessage(content: str="", role: str = "system"):
    return {"content": content, "role": role}


def UserMessage(content: str="", role: str = "user", function_call: Optional[Dict[str, Any]] = None):
    if content is None:
        content = ""
    return {"content": content, "role": role, "function_call": function_call}


def FunctionCall(name: str, arguments: Optional[Dict[str, Any]] = None):
    if arguments is None:
        arguments = {}
    return {"name": name, "arguments": arguments}


def AssistantMessage(content: str="", function_call: Optional[Dict[str, Any]] = None):
    if function_call is None:
        function_call = {}
    return {"content": content, "function_call": function_call, "role": "assistant"}


def FunctionMessage(name: str, content: str="", role: str = "function"):
    return {"content": content, "name": name, "role": role}


message_types = {
    "system": SystemMessage,
    "user": UserMessage,
    "assistant": AssistantMessage,
    "function": FunctionMessage,
}


class Cancelled(Exception):
    pass

class ConsumerClosed(Exception):
    pass

class ExceptionForAgent(Exception):
    """Base class for all exceptions that may occur inside a function that should be passed
    through to the agent, rather than stop the conversation."""
    pass


def messages_types_to_history(chat_history: list) -> list:
    return [i.chat for i in chat_history]

