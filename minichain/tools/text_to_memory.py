import datetime as dt
import hashlib
import uuid
from typing import Any, Dict, List, Optional, Union
import os

from pydantic import BaseModel, Field

from minichain.agent import Agent
from minichain.functions import Function
from minichain.schemas import Done
from minichain.dtypes import Cancelled
from minichain.utils.document_splitter import split_document


class ReadLater(BaseModel):
    url: str = Field(..., description="The url of the linked website.")
    expected_answers: List[str] = Field(..., description="List of question that we hope to find in this website")
    priority: Optional[int] = Field(0, description="The priority of the website - 100 is the highest priority, 0 is the lowest priority (default).")


class Memory(BaseModel):
    start_line: int = Field(
        ..., description="The line number where the memory starts in the document."
    )
    end_line: int = Field(
        ..., description="The line number where the memory ends in the document."
    )
    title: str = Field(
        ...,
        description="The title of this memory. Provide plain, unformatted text without links.",
    )
    relevant_questions: List[str] = Field(
        ...,
        description="Questions that are answered by the content of this memory. You will later be asked to find all memories related to arbitrary questions. Use this field to generate example questions for which you would like this memory to show up. Provide plain, unformatted questions without links.",
    )
    context: Optional[str] = Field(
        ...,
        description="Additional context for this memory. This should contain information from the previous sections that is needed to correctly understand the content. Provide plain, unformatted text without links.",
    )
    # type: memory / read-later
    type: str = Field(
        ...,
        description='The type of this memory. Allowed values are: ["content", "navigation", "further-reading"]. "navigation" and "further-reading" must include outgoing links in the "links" field.',
    )
    links: Optional[List[ReadLater]] = Field(
        None,
        description="List of links mentioned in this section to websites that you might want to read later.",
    )
    symbol_id: Optional[str] = Field(
        None,
        description="For source code: the id of the symbol that is described in this memory. Example: 'src/agent.py:Agent.run'",
    )



class MemoryMeta(BaseModel):
    source: str = Field(..., description="The source uri of the document.")
    content: str = Field(..., description="The content of the document.")
    watch_source: bool = Field(True, description="Whether to watch the source for changes - set to true for source files, set to False for conversational memories.")
    timestamp: dt.datetime = Field(default_factory=dt.datetime.now, description="The timestamp when the document was created.")
    scope: str = "root" # if scope is a conversation id, this memory will only appear for (sub)conversations with the same id

    # after loading: normalize source file paths
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if os.path.exists(self.source) and self.source.startswith("./"):
            self.source = self.source[2:]


class MemoryWithMeta(BaseModel):
    memory: Memory
    meta: MemoryMeta
    id: str = Field(
        description="A unique id for this memory. This is generated automatically.",
        default_factory=lambda: str(uuid.uuid4()),
    )


def add_line_numbers(text):
    lines = text.split("\n")
    numbered_lines = [f"{i + 1}: {line}" for i, line in enumerate(lines)]
    text_with_line_numbers = "\n".join(numbered_lines)
    return text_with_line_numbers

class EndThisMemorySession(Exception):
    pass

async def text_to_memory(text, source=None, agent_kwargs={}, existing_memories=[], return_summary=False) -> List[MemoryWithMeta]:
    """
    Turn a text into a list of semantic paragraphs.
    - add line numbers to the text
    - Split the text into pages with some overlap
    - Use an agent to create structured data from the text until it is done

    if text is specified with line numbers, lines can be skipped, which is used for updating memories of a file:
      ```
      1: line 1
      [Hidden: main function]
      20: line 20
      ```
    """
    existing_memories = list(existing_memories)
    memories = []

    lines = text.split("\n")

    async def add_memory(**memory):
        memory = Memory(**memory)
        if memory.links is None:
            memory.links = []
        content = "\n".join(lines[memory.start_line - 1 : memory.end_line])
        meta = MemoryMeta(source=source, content=content)
        memories.append(MemoryWithMeta(memory=memory, meta=meta))
        raise EndThisMemorySession

    add_memory_function = Function(
        name="add_memory",
        function=add_memory,
        openapi=Memory,
        description="Create a new memory.",
    )

    agent = Agent(
        name="TextToMemories",
        functions=[
            add_memory_function,
        ],
        system_message=f"Turn a text into a list of memories. A memory is one piece of information that is self-contained to understand but also atomic. You will use these memories later: you will be able to generate questions or keywords, and find the memories you are creating now. Remember only informative bits of information. The text has line numberes added at the beginning of each line, make sure to reference them when you create a memory. Parts of the text that you already created memories for are hidden (the memory title is added for context, but don't make new memories for the hidden sections). If the user provided text is a website, you will encounter navigation elements or sections with many outgoing links - especially to docs - remember them so you can read the referenced urls later. You can only see a section of a larger text at a time, so it can happen the the entirely text is irrelevant / consists out of references etc. In that case, directly end the session so that we can move on to the interesting parts. If most of the content is hidden and only single lines remain, don't memorize them unless they are super important - just end the conversation.",
        prompt_template="```\n{text}\n```".format,
        response_openapi=Done,
        **agent_kwargs,
    )
    done = False
    while not done:
        # Create one more memory
        to_remember = hide_already_memorized(text, existing_memories + memories)
        if not something_to_remember(to_remember):
            print("Nothing to remember.")
            break
        paragraphs = split_document(to_remember)
        try:
            for paragraph in paragraphs:
                print(paragraph)
                import tiktoken
                print("tokens:", len(tiktoken.encoding_for_model("gpt-3.5-turbo").encode(paragraph)))
                await agent.run(text=paragraph)
                # If the agent ran until the end, it means the agent didn't create a memory
            # if we come here, no memory was added for any paragraph
            done = True
        except EndThisMemorySession:
            continue
    if return_summary:
        return memories, hide_already_memorized(text, existing_memories + memories)
    else:
        return memories


async def text_to_single_memory(text=None, source=None, agent_kwargs={}) -> MemoryWithMeta:
    agent = Agent(
        name="TextToSingleMemory",
        functions=[],
        system_message="Describe the content of this text and turn provide structured metadata about it.",
        prompt_template="{text}".format,
        response_openapi=Memory,
        **agent_kwargs,
    )
    memory = await agent.run(text=text)
    meta = MemoryMeta(source=source, content=text)
    return MemoryWithMeta(memory=memory, meta=meta)


def hide_already_memorized(content, existing_memories):
    text_with_line_numbers = add_line_numbers(content)
    lines = text_with_line_numbers.split("\n")
    for memory in existing_memories:
        if memory.memory.start_line == memory.memory.end_line:
            # do not show first line of memory if the memory is only one line long
            lines[memory.memory.start_line - 1] = f"[Hidden: {memory.memory.title}]"
        else:
            fill_up_lines = memory.memory.end_line - memory.memory.start_line
            lines[
                memory.memory.start_line - 1 : memory.memory.end_line
            ] = [f"[{memory.meta.content.splitlines()[0]}\n" + \
                    f"    Hidden: {memory.memory.title}]"] + \
                    [None] * fill_up_lines
            
    lines = [i for i in lines if i is not None]
    text_with_line_numbers = "\n".join(lines)
    return text_with_line_numbers

def something_to_remember(content):
    lines = content.split("\n")
    # keep only lines that start with a number
    lines = [i for i in lines if len(i) > 0 and i[0].isdigit()]
    if len(lines) < 3:
        return False
    return True
