from typing import Any, List, Union, Dict
import json
import os
from uuid import uuid4
from collections import defaultdict
import asyncio

from minichain.utils.json_datetime import datetime_converter
from minichain.dtypes import Cancelled, ConsumerClosed, UserMessage
from minichain.utils.tokens import count_tokens
from minichain import settings


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
        self.ignore_keys = [k for k, v in self.current_message.items() if v is not None and v != "" and k!='function_call']
        self.shared = shared or {'on_message': do_nothing}
        self.active = True
        self.meta = meta or {}
    
    @property
    def context(self):
        """Returns the conversation object that contians this message"""
        return self.shared['message_db'].get(self.path[-2])
    
    async def prepare(self):
        """Send the path info so that the client knows where to put the message"""
        try:
            await self.shared['on_message']({
                "type": "set",
                "id": self.path[-1],
                "path": self.path,
                "meta": self.meta
            })
        except Exception as e:
            import traceback
            traceback.print_exc()
            # breakpoint()
    
    def off(self):
        """Turn the stream off and trigger saving"""
        self.active = False
    
    async def conversation(self, meta=None, **init_kwargs):
        """Create a new conversation"""
        conversation = Conversation(meta=meta, shared=self.shared, path=self.path, **init_kwargs)
        child_ids = self.meta["children"] + [conversation.path[-1]]
        await self.set(meta={"children": child_ids})
        return conversation

    async def chunk(self, diff=None, meta=None):
        if not self.active:
            return
        if meta is not None:
            nested("add", self.meta, meta)
            # we don't stream meta updates
        if diff is None:
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
            "path": self.path,
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


def datetime_or_str_to_datetime(value):
    if isinstance(value, str):
        return dt.datetime.fromisoformat(value)
    return value

def sort_by_timestamp(items):
    return sorted(items, key=lambda x: datetime_or_str_to_datetime(x.meta['timestamp']))

import datetime as dt
def get_default_meta(chat_summary=None):
    meta = {
        "timestamp": dt.datetime.now(),
    }
    if chat_summary is not None:
        meta["_chat_summary"] = chat_summary
    return meta

class Message():
    def __init__(self,
                 chat: Dict =None, # {role, content, function_call}
                 meta: Dict=None,
                 message_id: str=None,
                 path: List[str]=None,
                 shared=None):
        self.shared = shared
        self.chat = chat or {}
        self.meta = get_default_meta(chat)
        self.meta.update(meta or {})
        self.path = path or ['Trash']
        if message_id is None:
            message_id = str(uuid4().hex[:8])
            self.path = self.path + [message_id]
        self._stream_target = None
        self.shared['message_db'].register_message(self)
        self.meta['children'] = self.child_ids

    async def __aenter__(self):
        """Returns a stream target that can be used to update the message"""
        self._stream_target = StreamCollector(current_message=self.chat, meta=self.meta, path=self.path, shared=self.shared)
        await self._stream_target.prepare()
        return self._stream_target
    
    async def __aexit__(self, exc_type, exc_value, traceback):
        """saves the message to the message handler and avoids updating the message"""
        if self._stream_target is None:
            return
        # If this is the first time we exit from a stream to this message, set the duration field
        if 'duration' not in self._stream_target.meta:
            start_time = self._stream_target.meta['timestamp']
            duration = (dt.datetime.now() - start_time).total_seconds()
            await self._stream_target.set(meta={
                'duration': duration
            })
        self.chat = self._stream_target.current_message
        self.meta.update(self._stream_target.meta)
        self._stream_target.off()
        self.meta["_chat_summary"] = self.chat # will be overwritten by to_memory when needed
        self.save()

    async def to_memory(self):
        """Save the message to the memory of the conversation"""
        print("to_memory", self.chat)
        if self.meta.get('_memories') is not None:
            print("already in memory: ", self.meta)
            return
        conversation = self.shared['message_db'].get(self.path[-2])
        tokens = count_tokens(self.chat)
        self.meta['_tokens'] = tokens

        # check if this messages should be memorized
        function_call = self.chat.get('function_call', None) or {}
        action = function_call.get('name', None)
        function_response = self.chat.get("name", None)
        if (
            conversation.memory is None or
            action in ["find_memory", "upload_file_to_chat", "view", "return", "add_memory"] 
            or function_response in ["return", "upload_file_to_chat", "edit", "add_memory"]
            or self.meta.get("is_initial", False)
            or self.chat['role'] != 'user' and action is None
            or self.meta.get('deleted', False)
        ):
            self.meta['_memories'] = []
            self.meta['_outline'] = ""
            self.meta["_chat_summary"] = self.chat
            return
        
        print(conversation.meta, self.chat)
        async with self as handler:
            conversation.memory.register_message_handler(handler)
        
        if tokens > conversation.context_size * 0.2:
            memories, document_summary = await conversation.memory.ingest(
                self.as_document(),
                source=f"Message #{len(conversation.messages)}",
                scope=self.path[-2],
                watch_source=False,
                return_summary=True
            )
            self.meta['_memories'] = memories
            summary = (
                f"INFO: {self.chat['role']} has sent a message that is too long to display in full. Here is an outline of the sections of the message:\n" +
                document_summary
            )
            print(memories, "len:", len(memories))
            print(summary)
            input("press enter to continue")
            if self.chat.get('function_call', None) is not None and self.chat['function_call'].get('name', None) is not None:
                summary += f"\nThe message called the function: {self.chat['function_call']['name']}"
            summary += "\nEach section can be accessed by calling the `find_memory` function."
            self.meta['_chat_summary'] = {
                'role': self.chat['role'],
                'content': summary
            }
            self.meta['_outline'] = self.chat['role'] + ":\n" + "".join([f"- {i.memory.title}\n" for i in memories])
        else:
            memory = await conversation.memory.add_single_memory(
                source=f"Message #{len(conversation.messages)}",
                content=self.as_document(),
                scope=self.path[-2],
            )
            self.meta['_memories'] = [memory]
            self.meta['_outline'] =  self.chat['role'] + f": {memory.memory.title}"
            self.meta["_chat_summary"] = self.chat
        self.save()
    
    def as_document(self):
        document = f"Message from {self.chat['role']} {self.chat.get('name', '')}\n{self.chat['content']}"
        if (name:= (self.chat.get("function_call", None) or {}).get("name", None)) is not None:
            document += f"\n{self.chat['role']} invoked {name} with arguments: {json.dumps(self.chat['function_call']['arguments'], indent=2)}"
        return document
    
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
        if not os.path.exists(filepath + ".json"):
            return None
        with open(filepath + ".json", 'r') as f:
            data = json.load(f)
        message = cls(**data, **kwargs)
        # load all sub conversations
        if os.path.exists(filepath) and os.path.isdir(filepath):
            for sub_conversation_id in os.listdir(filepath):
                Conversation.load(os.path.join(filepath, sub_conversation_id, "conversation.json"), **kwargs)
        message.meta['children'] = message.child_ids
        return message
    
    @property
    def children(self):
        children = self.shared['message_db'].children_of(self.path[-1])
        return children
    
    @property
    def child_ids(self):
        return [c.path[-1] for c in self.children]
    
    def as_json(self):
        return {
            "chat": self.chat,
            "meta": self.meta,
            "path": self.path,
            "children": self.child_ids,
        }


class Conversation():
    def __init__(self,
                 path: List[str],
                 shared: Dict,
                 memory=None,
                 meta: Dict=None,
                 conversation_id: str=None,
                 messages: List[Message] = None,
                 insert_after: str=None,
                 forked_from: str=None,
                 context_size: int = 1024 * 128,
                 ):
        path = path or ['Trash']
        if conversation_id is None:
            conversation_id = str(uuid4().hex[:8])
            path = path + [conversation_id]
        self.meta = get_default_meta()
        self.meta.update(meta or {})
        self._messages = messages or []
        self.path = path
        self.shared = shared or {'on_message': do_nothing}
        self.shared['message_db'].register_conversation(self)
        self.forked_from = forked_from
        self.insert_after = insert_after
        self.context_size = context_size
        self.memory = memory
    
    @property
    def first_user_message(self):
        for m in self.messages:
            if m.meta.get('is_initial', False)==False and m.chat.get('role', None) == 'user':
                return m
        return None
    
    @property
    def messages(self):
        result = []
        if self.forked_from is not None:
            imported = self.shared['message_db'].get(self.forked_from[-2]).messages
            for i in imported:
                result.append(i)
                if i.path[-1] == self.forked_from[-1]:
                    break
                
        result += [i for i in self._messages if i is not None and i.meta.get('deleted', False)==False]
        return result
    
    async def fit_to_context(self):
        init_messages = [i for i in self.messages if i.meta.get('is_initial', False)]
        messages = [i for i in self.messages if i.meta.get('is_initial', False)==False]
        # Move original user message to init messages (where it does not get summarized)
        # unless it is very long
        if count_tokens(messages[0].chat) < self.context_size * 0.2:
            init_messages += [messages.pop(0)]
        # if there are no messages that could be summarized, return
        if len(messages) == 0:
            return [i.chat for i in init_messages]
        
        # replace old message by their outline iteratively - start by replacing 0 (change nothing)
        while True:
            for i, message in enumerate(messages):
                summarized = [i.chat for i in init_messages] + [
                    UserMessage(
                        "Our chat history is already quite long. Here are the topics we discussed earlier:\n" + 
                        "\n".join([i.meta['_outline'] for i in messages[:i]])
                    )
                ][:i] +[
                    i.meta['_chat_summary'] for i in messages[i:] 
                ]
                total_tokens = sum([count_tokens(j) for j in summarized])
                if total_tokens < self.context_size * 0.8:
                    return summarized
                print(total_tokens, "do not fit into context - summarizing", i)
                await message.to_memory()
                # before .to_memory is called, _chat_summary is a copy of the original message. We now also call it for the most recent message
                # to replace very long messages with a summary, without replacing the entire conversation by an outline
                await messages[-1].to_memory()
            # if we get here, we have summarized all messages, but they still don't fit into the context
            # we now cutoff from the beginning
            messages = messages[len(messages)//2:]
    
    def fork(self, message_id, new_path=None):
        """Returns a new conversation that is forked from the given message_id"""
        if new_path is None:
            new_path = self.path + [message_id, str(uuid4().hex[:8])]
        return Conversation(
            path=new_path,
            conversation_id=new_path[-1],
            shared=self.shared,
            meta=self.meta,
            forked_from=self.path + [message_id],
            context_size=self.context_size
        )
    
    async def set(self, **meta):
        self.meta.update(meta)
    
    def to(self, chat, meta=None):
        """returns a new Message object"""
        meta = dict(**(meta or {}))
        if self.insert_after is not None:
            meta['insert_after'] = self.insert_after
        message = Message(chat=chat, path=self.path, shared=self.shared, meta=meta)
        if self.insert_after is None:
            self._messages.append(message)
        else:
            for i, m in enumerate(self._messages):
                if m is None:
                    continue
                if m.path[-1] == self.insert_after:
                    self._messages.insert(i+1, message)
                    break
        self.save()
        return message

    def at(self, message_id, meta=None):
        """returns a new conversation that inserts messages not at the end, but after the given message_id"""
        meta = dict(**self.meta, **(meta or {}))
        return Conversation(
            path=self.path,
            messages=self._messages,
            conversation_id=[self.path[-1]],
            shared=self.shared,
            meta=meta,
            insert_after=message_id,
            context_size=self.context_size
        )
    
    async def __aenter__(self):
        # Send the path message to the client
        await self.set()
        self.save()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        self.save()

    def save(self):
        target_dir = self.shared['save_dir'] + "/" + "/".join(self.path)
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
        filepath = os.path.join(target_dir, "conversation.json")
        data = self.as_json()
        data['conversation_id'] = self.path[-1]
        data['message_ids'] = [m['path'][-1] for m in data.pop('messages')]
        with open(filepath, 'w') as f:
            json.dump(data, f, default=datetime_converter)
    
    @classmethod
    def load(cls, filepath, **kwargs):
        with open(filepath, 'r') as f:
            data = json.load(f)
            message_ids = data.pop('message_ids', [])
        conversation = cls(**data, **kwargs)
        for message_id in message_ids:
            message = Message.load(os.path.join(os.path.dirname(filepath), message_id), **kwargs)
            conversation._messages.append(message)
        return conversation
    
    async def send(self, chat_message, **meta):
        """Send a message without streaming - for initial messages
        
        Arguments:
            chat_message {dict} -- e.g. {"role": "assistant", "content": "Hello"}
        """
        async with self.to(chat_message, meta) as stream:
            await stream.set(chat_message)
    
    def as_json(self):
        return {
            "meta": self.meta,
            "path": self.path,
            "messages": [m.as_json() for m in self.messages]
        }


class MessageDB():
    def __init__(self, save_dir=".minichain/messages", on_message=None):
        if settings.default_memory is None:
            import minichain.memory
        self.memory = settings.default_memory
        on_message = on_message or do_nothing
        self.shared = {
            'on_message': self.on_message,
            'consumers': defaultdict(list),
            'message_db': self,
            'save_dir': save_dir
        }
        self.conversations = []
        self.messages = []
        self.load()
        self.meta = {
            "path": ["root"]
        }
        self._cancelled = []
    
    def cancel(self, conversation_id):
        self._cancelled.append(conversation_id)
    
    async def on_message(self, msg):
        # send the message to all other consumers if they want to consume it
        path = msg.get("path", None)
        if path is None:
            if (message := self.get_message(msg['id'])) is not None:
                path = message.path
            else:
                path = self.get(msg['id']).path
        not_yet_raised = []
        raise_now = False
        for cancelled in self._cancelled:
            if cancelled in path:
                raise_now = True
            else:
                not_yet_raised.append(cancelled)
        self._cancelled = not_yet_raised
        if raise_now:
            raise Cancelled()

        """
        we send to subscribers of:
        path[-2] -> normal message of this conversation
        path[-1] -> messages addressed to the conversation itsefl, e.g. meta updates. should actually not be used
        """
        for target in path[-2:]:
            await self.send_to_consumers(target, msg)
    
    async def send_to_consumers(self, target, msg):
        alive = []
        consumers = self.shared['consumers'].get(target, [])
        for consume in consumers:
            try:
                await consume(msg)
                alive += [consume]
            except ConsumerClosed:
                print("Consumer closed")
        self.shared['consumers'][target] = alive
    
    def register_conversation(self, conversation):
        if not conversation.path[-1] in [c.path[-1] for c in self.conversations]:
            self.conversations.append(conversation)
    
    def register_message(self, message):
        self.messages.append(message)
    
    def get_message(self, message_id):
        for message in self.messages:
            if message.path[-1] == message_id:
                return message
    
    async def update_message_meta(self, message_id, meta):
        message = self.get_message(message_id)
        if message is None:
            return
        message.meta.update(meta)
        message.save()
        await self.shared['on_message']({
            "type": "set",
            "id": message_id,
            "meta": message.meta,
            "chat": message.chat,
            "path": message.path
        })
        return message
    
    async def update_conversation_meta(self, conversation_id, meta):
        conversation = self.get(conversation_id)
        if conversation is None:
            return
        conversation.meta.update(meta)
        conversation.save()
        await self.shared['on_message']({
            "type": "set",
            "id": conversation_id,
            "meta": conversation.meta,
            "chat": conversation.messages[-1].chat,
            "path": conversation.path
        })
        return conversation
    
    async def update_meta(self, any_id, meta):
        updated = await self.update_message_meta(any_id, meta)
        if updated is None:
            updated = await self.update_conversation_meta(any_id, meta)
        return updated
    
    async def update_message(self, message_id, update):
        message = self.get_message(message_id)
        if message is None:
            return
        async with message as stream:
            await stream.set(update)
        return message

    def children_of(self, message_id):
        return [c for c in self.conversations if c.path[-2] == message_id and c.meta.get('deleted', False)==False]
    
    def add_consumer(self, consumer, conversation_id):
        self.shared['consumers'][conversation_id].append(consumer)

    def load(self):
        load_dir = self.shared['save_dir'] + "/root"
        if not os.path.exists(load_dir):
            return
        # in load_dir, we have one folder for each conversation
        for conversation_id in os.listdir(load_dir):
            Conversation.load(os.path.join(load_dir, conversation_id, "conversation.json"), shared=self.shared)

    def get(self, conversation_id) -> Conversation:
        if conversation_id == "root":
            return self
        for conversation in self.conversations:
            if conversation.path[-1] == conversation_id:
                return conversation

    async def conversation(self, meta=None, **init_kwargs) -> Conversation:
        conversation = Conversation(meta=meta, shared=self.shared, path=['root'], **init_kwargs)
        return conversation
    
    def as_json(self, agent=None):
        # We return the same format as conversations, but we show only user messages that contain conv.meta['preview']
        conversations = self.children_of('root')
        conversations = sort_by_timestamp(conversations)
        if agent:
            conversations = [c for c in conversations if c.meta.get('agent') == agent]

        messages = [c.first_user_message for c in conversations]
        messages = [dict(chat=m.chat, path=c.path, meta=c.meta, fake_children=[c.path[-1]], agent=c.meta.get('agent')) for m, c in zip(messages, conversations) if m is not None]
        for m in messages:
            m['meta']['children'] = m.pop('fake_children')
        return {
            "meta": self.meta,
            "path": ['root'],
            "messages": messages
        }



def nested(mode, dictionary, value):
    if not isinstance(value, dict):
        if dictionary is None and value is None:
            return None
        if dictionary is None and isinstance(value, str):
            dictionary = ""
        if mode == "add" and isinstance(dictionary, list):
            return dictionary + (value or [])
        elif mode == "add" and isinstance(value, list):
            return (dictionary or []) + value
        elif mode == "add":
            return dictionary + (value or "")
        elif mode == "set":
            return value
    if dictionary is None:
        dictionary = {}
    for k, v in value.items():
        dictionary[k] = nested(mode, dictionary.get(k, None), v)
    return dictionary
