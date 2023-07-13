import uuid
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from minichain.agent import Agent, Function, SystemMessage, Done
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
        description="Tags that describe the content of this memory. You will later be asked to find all memories related to arbitrary tags. Use this field to generate example tags for which you would like this memory to show up. Don't 'pollute' good tags with uninformative memories, as this will make it harder to retrieve the good memories later.",
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



def text_to_memory(text, source=None) -> List[MemoryWithMeta]:
    """
    Turn a text into a list of semantic paragraphs.
    - add line numbers to the text
    - Split the text into pages with some overlap
    - Use an agent to create structured data from the text until it is done
    """
    memories = []
    lines = text.split("\n")

    numbered_lines = [f"{i}: {line}" for i, line in enumerate(lines)]
    text_with_line_numbers = "\n".join(numbered_lines)
    paragraphs = split_document(text_with_line_numbers, words=3000)
    current_paragraph_start = 0
    current_paragraph_end = len(paragraphs[0].split("\n")) - 1

    def add_memory(**memory):
        memory = Memory(**memory)
        progress = max([0] + [i.memory.end_line for i in memories if i.meta.source == source])
        content = "\n".join(lines[memory.start_line : memory.end_line + 1])
        warning = ""
        if memory.start_line < current_paragraph_start or memory.end_line > current_paragraph_end:
            return f"Fatal error: you are trying to add a memory referencing lines that are currently not visible to you. ."
        if len(memories) > 2 and memory.end_line <= memories[-2].memory.end_line:
            return f"Memory ignored because you already scanned the document until line: {memories[-1].memory.end_line}. Provide a start_line and end_line that are both larger than {memories[-1].memory.end_line}. Left to-do are lines: lines {progress}-{current_paragraph_end}"
        elif len(content.split()) < 50:
            warning = "\nWarning: this original content of this memory is too short, please package the document into larger snippets."
        if len(memories) > 1 and memory.start_line <= memories[-1].memory.end_line:
            warning += "\nSerious warning: this memory overlaps with the previous memory. This is should be a rare exception, usually we should move on in the document."
        if memory.end_line >= current_paragraph_end - 5:
            warning = "You can end the session by using the return function."
        meta = MemoryMeta(source=source, content=content)
        memories.append(MemoryWithMeta(memory=memory, meta=meta))
        progress = max([0] + [i.memory.end_line for i in memories])
        # print(f"Added memory: {memories[-1]}.")
        return f"Memory added. Left to-do are lines: lines {progress}-{current_paragraph_end}.{warning}"

    add_memory_function = Function(
        name="add_memory",
        function=add_memory,
        openapi=Memory,
        description="Add a memory to the memory list. Remember only useful information, skip over references, links, navbars, or other uninformative text. Memories should usually be self-contained and atomic and include 10-1000 lines of text. Create memories for the earlier parts of the document first - don't create memories out of order.",
    )

    
    agent = Agent(
        functions=[
            add_memory_function,
        ],
        system_message=SystemMessage(
            "Turn a text into a list of memories. A memory is one piece of information that is self-contained to understand but also atomic. You will use these memories later: you will be able to generate questions or keywords, and find the memories you are creating now. Ignore uninformative text sections like website navigation elements, urls/links, reference sections, etc. Remember only informative bits of information. The text has line numberes added at the beginning of each line, make sure to reference them when you create a memory.  Make sure to add all memories before you end the conversation by responding with a 'content' instead of a 'function_call'. If you get stuck while creating a memory just move on the a later section of the text. You can only see a section of a larger text at a time, so it can happen the the entirely text is irrelevant / consists out of references etc. In that case, directly end the session so that we can move on to the interesting parts."
        ),
        prompt_template="{text}".format,
        keep_first_messages=1,
        keep_last_messages=5,
        response_openapi=Done
    )

    for paragraph in paragraphs:
        current_paragraph_start = int(paragraph.split("\n")[0].split(":")[0])
        current_paragraph_end = int(paragraph.split("\n")[-2].split(":")[0]) + 1
        print("num_memories:", len(memories))
        agent.run(text=paragraph)
    return memories.copy()
