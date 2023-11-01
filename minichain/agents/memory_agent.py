import asyncio

from pydantic import BaseModel, Field

from minichain.agent import Agent
from minichain.dtypes import UserMessage
from minichain.memory import SemanticParagraphMemory
from minichain.tools import codebase


class ProgrammerResponse(BaseModel):
    content: str = Field(..., description="The final response to the user.")


# Get the system message from the source dir of this file: memory_agent.prompt
with open(__file__.replace(".py", ".prompt"), "r") as f:
    system_message = f.read()


class MinichainHelp(Agent):
    def __init__(self, memory=None, load_memory_from=None, **kwargs):
        memory = memory or SemanticParagraphMemory(agents_kwargs=kwargs)
        if load_memory_from:
            try:
                memory.load(load_memory_from)
            except FileNotFoundError:
                print(f"Memory file {load_memory_from} not found.")
        print("Init history for programmer:", kwargs.get("init_history", []))
        init_history = kwargs.pop("init_history", [])
        if init_history == []:
            user_msg = f"Here is a summary of the project we are working on: \n{codebase.get_initial_summary()}."
            if len(memory.memories) > 0:
                user_msg += f"\nHere is a summary of your memory: \n{memory.get_content_summary()}"
            else:
                user_msg += f"\nYou don't have any memories yet."
            init_history.append(UserMessage(user_msg))
        super().__init__(
            functions=[
                memory.find_memory_tool(),
                memory.ingest_tool(),
            ],
            system_message=system_message,
            prompt_template="{query}".format,
            response_openapi=ProgrammerResponse,
            init_history=init_history,
            **kwargs,
        )
        self.memory = memory

    async def before_run(self, *args, **kwargs):
        self.memory.reload()

    def register_message_handler(self, message_handler):
        self.memory.register_message_handler(message_handler)
        super().register_message_handler(message_handler)


async def main():
    memory = SemanticParagraphMemory(use_vector_search=True)
    test_file = "minichain/utils/docker_sandbox.py"
    with open(test_file, "r") as f:
        content = f.read()
    await memory.ingest(content, test_file)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
