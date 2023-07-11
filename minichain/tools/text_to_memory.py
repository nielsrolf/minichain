import uuid
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from minichain.agent import Agent, Function, SystemMessage
from minichain.utils.document_splitter import split_document
from minichain.utils.markdown_browser import markdown_browser


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
    tags: List[str] = Field(
        ...,
        description="Tags that describe the content of this memory. You will later be asked to find all memories related to arbitrary tags. Use this field to generate example tags for which you would like this memory to show up.",
    )
    context: Optional[str] = Field(
        ...,
        description="Additional context for this memory. This should contain information from the previous sections that is needed to correctly understand the content. Provide plain, unformatted text without links.",
    )


class MemoryMeta(BaseModel):
    source: str = Field(..., description="The source uri of the document.")
    content: str = Field(..., description="The content of the document.")


class MemoryWithMeta(BaseModel):
    memory: Memory
    meta: MemoryMeta
    id: str = Field(
        description="A unique id for this memory. This is generated automatically.",
        default_factory=lambda: str(uuid.uuid4()),
    )


def text_to_memory(text, source=None):
    """
    Turn a text into a list of semantic paragraphs.
    - add line numbers to the text
    - Split the text into pages with some overlap
    - Use an agent to create structured data from the text until it is done
    """
    memories = []
    lines = text.split("\n")

    def add_memory(**memory):
        memory = Memory(**memory)
        content = "\n".join(lines[memory.start_line : memory.end_line + 1])
        warning = ""
        if len(content.split()) < 50:
            warning = " This memory is very short. Please try to group content into larger packages of at least 50 words."
        meta = MemoryMeta(source=source, content=content)
        memories.append(MemoryWithMeta(memory=memory, meta=meta))
        print(f"Added memory: {memories[-1]}")
        return f"Memory added.{warning}"

    add_memory_function = Function(
        name="add_memory",
        function=add_memory,
        openapi=Memory,
        description="Add a memory to the memory list.",
    )

    numbered_lines = [f"{i}: {line}" for i, line in enumerate(lines)]
    text_with_line_numbers = "\n".join(numbered_lines)
    paragraphs = split_document(text_with_line_numbers, words=3000)
    agent = Agent(
        functions=[
            add_memory_function,
        ],
        system_message=SystemMessage(
            "Turn a text into a list of memories. A memory is one piece of information that is self-contained to understand but also atomic. You will use these memories later: you will be able to generate questions or keywords, and find the memories you are creating now. Ignore uninformative text sections like website navigation elements, urls/links, lists of references, etc. Remember only informative bits of information. The text has line numberes added at the beginning of each line, make sure to reference them when you create a memory.  Make sure to add all memories before you end the conversation by responding with a 'content' instead of a 'function_call'."
        ),
        prompt_template="{text}".format,
        keep_first_messages=1,
        keep_last_messages=3,
    )
    for paragraph in paragraphs:
        agent.run(text=paragraph)
    return memories
