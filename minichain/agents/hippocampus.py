from typing import List, Optional

from pydantic import BaseModel, Field

from minichain.agent import Agent
from minichain.dtypes import SystemMessage, UserMessage
from minichain.memory import SemanticParagraphMemory
from minichain.tools import codebase
from minichain.tools.bash import Jupyter


system_message = """You are the memory assistant.
Your task is to find revelant memories or code sections for the user.
Use the following strategy:
- first, search for relevant memories using the `find_memory` function
- if this doesn't yield the desired information, use the other tools to explore the files or try searching related questions in the memory
- your task is only to find relevant memories or code sections, everything else is out of scope
"""

class CodeSection(BaseModel):
    path: str = Field(..., description="The path to the file.")
    start: int = Field(..., description="The start line of the code section.")
    end: int = Field(..., description="The end line of the code section.")
    summary: str = Field(..., description="Very brief summary of what happens in the code section.")


class RelevantInfos(BaseModel):
    code_sections: List[CodeSection] = Field(..., description="Code sections that are relevant to the query.")
    answer: str = Field(..., description="The answer to the query.")


class Hippocampus(Agent):
    def __init__(self, load_memory_from=None, **kwargs):
        memory = SemanticParagraphMemory(agents_kwargs=kwargs)
        try:
            memory.load(load_memory_from)
        except FileNotFoundError:
            print(f"Memory file {load_memory_from} not found.")

        functions = [
            memory.find_memory_tool(),
            Jupyter(),
            codebase.get_file_summary,
            codebase.view,
        ]
        
        super().__init__(
            functions=functions,
            system_message=system_message,
            prompt_template="Find memories related to: {query}".format,
            response_openapi=RelevantInfos,
            **kwargs,
        )
        self.memory = memory
    
    async def before_run(self, *args, **kwargs):
        self.memory.reload()

    def register_message_handler(self, message_handler):
        self.memory.register_message_handler(message_handler)
        return super().register_message_handler(message_handler)
    
    @property
    def init_history(self):
        init_msg = f"Here is a summary of the project we are working on: \n{codebase.get_initial_summary()}"
        if self.memory and len(self.memory.memories) > 0:
            init_msg += f"\nHere is a summary of your memory: \n{self.memory.get_content_summary()}\nUse the `find_memory` function to find relevant memories."
        init_history = [
            SystemMessage(self.system_message),
            UserMessage(init_msg)
        ]
        return init_history

