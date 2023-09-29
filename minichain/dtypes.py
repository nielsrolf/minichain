import uuid
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional
import json


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

