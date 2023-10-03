import asyncio

from pydantic import BaseModel, Field

from minichain.agent import Agent, SystemMessage, UserMessage
from minichain.memory import SemanticParagraphMemory
from minichain.tools import codebase
from minichain.tools.bash import CodeInterpreter


async def async_print(i, final=False):
    # print(i)
    pass


class Programmer(Agent):
    def __init__(self, memory=None, load_memory_from=None, **kwargs):
        self.memory = memory
        if load_memory_from:
            if not memory:
                self.memory = SemanticParagraphMemory(
                    use_vector_search=True, agents_kwargs=kwargs
                )
            self.memory.load(load_memory_from)
        interpreter = CodeInterpreter()
        self.interpreter = interpreter
        print("Init history for programmer:", kwargs.get("init_history", []))
        init_history = kwargs.pop("init_history", [])
        if init_history == []:
            init_history.append(
                UserMessage(
                    f"Here is a summary of the project we are working on: \n{codebase.get_initial_summary()}"
                )
            )
        functions = [
            interpreter.bash,
            interpreter,
            codebase.get_file_summary,
            codebase.view,
            codebase.edit,
            codebase.scan_file_for_info,
        ]
        if self.memory:
            functions += [
                self.memory.find_memory_tool(),
            ]
        super().__init__(
            functions=functions,
            system_message="You are an expert programmer. You can do a wide range of tasks, such as implementing features, debugging and refactoring code, writing docs, etc. using bash commands. Avoid interactive commands, outputs are only send when a command finished execution. When you implement something, write code, and run tests to make sure it works. If the user asks you to do something (e.g. make a plot, install a package, etc.), do it using the bash and python functions, and explain what you did instead of responding to the user directly. When something doesn't work on the first try, try to find a way to fix it before asking the user for help.",
            prompt_template="{query}".format,
            init_history=init_history,
            **kwargs,
        )
