import json
import uuid
from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional


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
        if isinstance(self.function_call, dict):
            self.function_call = FunctionCall(**self.function_call)

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


message_types = {
    "system": SystemMessage,
    "user": UserMessage,
    "assistant": AssistantMessage,
    "function": FunctionMessage,
}


class Cancelled(Exception):
    pass


def messages_types_to_history(chat_history: list) -> list:
    if not isinstance(chat_history[0], dict):
        messages = []
        for i in chat_history:
            # print(i)
            message = i.dict()
            # delete the parent field
            messages.append(message)
    else:
        messages = chat_history

    # remove function calls from messages if they are None
    for message in messages:
        message.pop("parent", None)
        message.pop("id", None)
        message.pop("conversation_id", None)
        # delete all fields that are None
        for k, v in dict(**message).items():
            if v is None and not k == "content":
                message.pop(k)
    return messages
