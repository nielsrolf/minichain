from typing import Any, List, Union, Dict
import json
import os
from uuid import uuid4

from minichain.utils.json_datetime import datetime_converter

async def do_nothing(*args, **kwargs):
    pass

async def async_print(*args, **kwargs):
    print(*args, **kwargs)


class StreamCollector():
    """Collects chunks and forwards them to the client.
    
    prepare() is sent first to tell the client where to put the message.
    set() replaces the message with the given chat.
    chunk() adds the given diff to the message.
    """
    def __init__(self, path: List[str] = ["Trash"], current_message: Dict = None, meta: Dict = None, shared: Dict = None):
        self.path = path
        self.current_message = current_message or {}
        self.ignore_keys = [k for k, v in self.current_message.items() if v is not None and v != ""]
        self.shared = shared or {'on_message': do_nothing}
        self.active = True
        self.meta = meta or {}
    
    async def prepare(self):
        """Send the path info so that the client knows where to put the message"""
        try:
            await self.shared['on_message']({
                "type": "path",
                "path": self.path,
                "meta": self.meta
            })
        except Exception as e:
            import traceback
            traceback.print_exc()
            breakpoint()
    
    def off(self):
        """Turn the stream off and trigger saving"""
        self.active = False
    
    def conversation(self, meta=None):
        """Create a new conversation"""
        return Conversation(meta=meta, shared=self.shared, path=self.path)

    async def chunk(self, diff):
        if not self.active:
            return
        if isinstance(diff, str):
            diff = {"content": diff}
        for key in self.ignore_keys:
            diff.pop(key, None)
            
        nested("add", self.current_message, diff)

        msg = {
            "id": self.path[-1],
            "type": "chunk",
            "diff": diff
        }
        await self.shared['on_message'](msg)

    async def set(self, chat=None, meta=None):
        if not self.active:
            return
        if chat is not None:
            if isinstance(chat, str):
                chat = {"content": chat}
            self.current_message.update(chat)
        if meta is not None:
            self.meta.update(meta)
        msg = {
            "id": self.path[-1],
            "type": "set",
            "chat": self.current_message,
            "meta": self.meta
        }
        await self.shared['on_message'](msg)
    
    async def __call__(self, diff):
        """Act as a stream target for a function"""
        await self.chunk(diff)


class StreamToStdout(StreamCollector):
    """Can be used as default stream target for agents that are not connected to a client"""
    def __init__(self):
        super().__init__(shared={'on_message': async_print})

def sort_by_timestamp(items):
    return sorted(items, key=lambda x: x.meta['timestamp'])

import datetime as dt
def get_default_meta():
    return {
        "timestamp": dt.datetime.now(),
    }

class Message():
    def __init__(self,
                 chat: Dict =None, # {role, content, function_call}
                 meta: Dict=None,
                 message_id: str=None,
                 path: List[str]=None,
                 shared=None):
        self.chat = chat or {}
        self.meta = get_default_meta()
        self.meta.update(meta or {})
        self.path = path or ['Trash']
        if message_id is None:
            message_id = str(uuid4().hex[:8])
            self.path = self.path + [message_id]
        self._stream_target = None
        self.shared = shared

    async def __aenter__(self):
        """Returns a stream target that can be used to update the message"""
        self._stream_target = StreamCollector(current_message=self.chat, meta=self.meta, path=self.path, shared=self.shared)
        await self._stream_target.prepare()
        return self._stream_target
    
    async def __aexit__(self, exc_type, exc_value, traceback):
        """saves the message to the message handler and avoids updating the message"""
        self.chat = self._stream_target.current_message
        self.meta.update(self._stream_target.meta)
        self._stream_target.off()
        self.save()
    
    def save(self):
        target_dir = self.shared['save_dir'] + "/" + "/".join(self.path[:-1])
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
        filepath = os.path.join(target_dir, f"{self.path[-1]}.json")
        with open(filepath, 'w') as f:
            json.dump({
                "chat": self.chat,
                "meta": self.meta,
                "path": self.path,
                "message_id": self.path[-1],
            }, f, default=datetime_converter)
    
    @classmethod
    def load(cls, filepath, **kwargs):
        with open(filepath, 'r') as f:
            data = json.load(f)
        return cls(**data, **kwargs)
    
    @property
    def children(self):
        children = self.shared['message_db'].get(self.path[-1])
        return children
    
    def as_json(self):
        children = self.children
        child_ids = [c.path[-1] for c in children]
        return {
            "chat": self.chat,
            "meta": self.meta,
            "path": self.path,
            "children": child_ids,
        }


class Conversation():
    def __init__(self,
                 path: List[str],
                 meta: Dict=None,
                 conversation_id: str=None,
                 messages: List[Message] = None,
                 shared: Dict = None):
        path = path or ['Trash']
        if conversation_id is None:
            conversation_id = str(uuid4().hex[:8])
            path = path + [conversation_id]
        self.meta = get_default_meta()
        self.meta.update(meta or {})
        self.messages = messages or []
        self.path = path
        self.shared = shared or {'on_message': do_nothing}
    
    def set(self, **meta):
        self.meta.update(meta)
        self.shared['on_message']({
            "type": "path",
            "path": self.path,
            "meta": self.meta
        })
    
    def to(self, chat, meta=None):
        """returns a new Message object"""
        self.save()
        message = Message(chat=chat, path=self.path, shared=self.shared, meta=meta)
        self.messages.append(message)
        return message
    
    async def __aenter__(self):
        # Send the path message to the client
        await self.set()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        self.save()

    def save(self):
        target_dir = self.shared['save_dir'] + "/" + "/".join(self.path)
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
        filepath = os.path.join(target_dir, "conversation.json")
        with open(filepath, 'w') as f:
            json.dump({
                "meta": self.meta,
                "path": self.path,
                "conversation_id": self.path[-1],
            }, f, default=datetime_converter)
        for message in self.messages:
            message.save()
    
    @classmethod
    def load(cls, filepath, **kwargs):
        with open(filepath, 'r') as f:
            data = json.load(f)
        return cls(**data, **kwargs)
    
    async def send(self, chat_message, **meta):
        """Send a message without streaming - for initial messages
        
        Arguments:
            chat_message {dict} -- e.g. {"role": "assistant", "content": "Hello"}
        """
        # if the message is not
        async with self.to(chat_message, meta) as stream:
            await stream.set(chat_message)
    
    def as_json(self):
        return {
            "meta": self.meta,
            "path": self.path,
            "messages": [m.as_json() for m in sort_by_timestamp(self.messages)]
        }


class MessageDB():
    def __init__(self, save_dir=".minichain/messages", on_message=None):
        on_message = on_message or do_nothing
        self.shared = {
            'on_message': self.on_message,
            'consumers': [on_message],
            'message_db': self,
            'save_dir': save_dir
        }
        self.conversations = []
    
    async def on_message(self, msg):
        for consume in self.shared['consumers']:
            await consume(msg)
    
    def add_consumer(self, consumer):
        self.shared['consumers'].append(consumer)

    def load(self):
        load_dir = self.shared['save_dir'] + "/root"
        if not os.path.exists(load_dir):
            return
        # in load_dir, we have one folder for each conversation
        for conversation_id in os.listdir(load_dir):
            conversation = Conversation.load(os.path.join(load_dir, conversation_id, "conversation.json"), shared=self.shared)
            self.conversations.append(conversation)

    def get(self, conversation_id) -> Conversation:
        if conversation_id == "root":
            return self
        for conversation in self.conversations:
            if conversation.path[-1] == conversation_id:
                return conversation

    def conversation(self, meta=None) -> Conversation:
        conversation = Conversation(meta=meta, shared=self.shared, path=['root'])
        self.conversations.append(conversation)
        return conversation
    
    def as_json(self):
        # We return the same format as conversations, but we show only user messages that contain conv.meta['preview']
        conversations = sort_by_timestamp(self.conversations)
        conversations = [i for i in conversations if i.path]


def nested(mode, dictionary, value):
    if not isinstance(value, dict):
        if dictionary is None and value is None:
            return None
        if dictionary is None and isinstance(value, str):
            dictionary = ""
        if mode == "add":
            return dictionary + (value or "")
        elif mode == "set":
            return value
    if dictionary is None:
        dictionary = {}
    for k, v in value.items():
        dictionary[k] = nested(mode, dictionary.get(k, None), v)
    return dictionary
