import asyncio

from pydantic import BaseModel, Field

from minichain.agent import Agent, SystemMessage, UserMessage
from minichain.memory import SemanticParagraphMemory
from minichain.tools import codebase



class ProgrammerResponse(BaseModel):
    content: str = Field(..., description="The final response to the user.")


async def async_print(i, final=False):
    # print(i)
    pass


class MemoryAgent(Agent):
    def __init__(self, silent=False, on_stream_message=async_print, memory=None, load_memory_from=None, **kwargs):
        self.memory = memory or SemanticParagraphMemory(use_vector_search=True, agents_kwargs=kwargs)
        if load_memory_from:
            self.memory.load(load_memory_from)
        print("Init history for programmer:", kwargs.get("init_history", []))
        init_history = kwargs.pop("init_history", [])
        if init_history == []:
            user_msg = f"Here is a summary of the project we are working on: \n{codebase.get_initial_summary()}."
            if len(self.memory.memories) > 0:
                user_msg += f"\nHere is a summary of your memory: \n{self.memory.get_content_summary()}"
            else:
                user_msg += f"\nYou don't have any memories yet."
            init_history.append(
                UserMessage(
                    user_msg
                )
            )
        super().__init__(
            functions=[
                # interpreter.bash,
                # interpreter,
                # codebase.get_file_summary,
                # codebase.view,
                # codebase.edit,
                # # codebase.view_symbol,
                # # codebase.replace_symbol,
                # codebase.scan_file_for_info,
                self.memory.find_memory_tool(),
                self.memory.ingest_tool(),
            ],
            system_message=SystemMessage(
                "You are an expert programmer. You find relevant code sections by using the remember tool."
            ),
            prompt_template="{query}".format,
            silent=silent,
            response_openapi=ProgrammerResponse,
            init_history=init_history,
            **kwargs,
        )





async def main():
    memory = SemanticParagraphMemory(use_vector_search=True)
    test_file = "minichain/utils/docker_sandbox.py"
    with open(test_file, "r") as f:
        content = f.read()
    await memory.ingest(content, test_file)
    



if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
