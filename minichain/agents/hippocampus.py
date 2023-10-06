from typing import List, Optional

from pydantic import BaseModel, Field

from minichain.agent import Agent
from minichain.dtypes import AssistantMessage, FunctionCall, UserMessage, FunctionMessage
from minichain.memory import SemanticParagraphMemory
from minichain.tools import codebase
from minichain.tools.bash import CodeInterpreter


system_message = """You are the memory assistant.
Your task is to find revelant memories or code sections for the user.
Use the following strategy:
- first, search for relevant memories using the `find_memory` function
- if this doesn't yield the desired information, use the other tools to explore the files or try searching related questions in the memory
"""

class CodeSection(BaseModel):
    path: str = Field(..., description="The path to the file.")
    start_line: int = Field(..., description="The start line of the code section.")
    end_line: int = Field(..., description="The end line of the code section.")
    summary: str = Field(..., description="Very brief summary of what happens in the code section.")


class RelevantInfos(BaseModel):
    code_sections: List[CodeSection] = Field([], description="Code sections that are relevant to the query.")
    answer: Optional[str] = Field(None, description="The answer to the query.")


class Hippocampus(Agent):
    def __init__(self, load_memory_from=None, **kwargs):
        self.memory = SemanticParagraphMemory(
            use_vector_search=True, agents_kwargs=kwargs
        )
        try:
            self.memory.load(load_memory_from)
        except FileNotFoundError:
            print(f"Memory file {load_memory_from} not found.")
        interpreter = CodeInterpreter()

        functions = [
            self.memory.find_memory_tool(),
            interpreter.bash,
            interpreter,
            codebase.get_file_summary,
            codebase.view,
            codebase.edit,
            codebase.scan_file_for_info,
        ]
        init_msg = f"Here is a summary of the project we are working on: \n{codebase.get_initial_summary()}"
        if self.memory and len(self.memory.memories) > 0:
            init_msg += f"\nHere is a summary of your memory: \n{self.memory.get_content_summary()}\nUse the `find_memory` function to find relevant memories."
        init_history = [UserMessage(init_msg)]
        super().__init__(
            functions=functions,
            system_message=system_message,
            prompt_template="{query}".format,
            init_history=init_history,
            response_openapi=RelevantInfos,
            **kwargs,
        )

    def register_stream(self, stream):
        self.memory.register_stream(stream)
        return super().register_stream(stream)

