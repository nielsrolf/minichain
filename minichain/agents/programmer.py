import asyncio

from pydantic import BaseModel, Field

from minichain.agent import Agent
from minichain.dtypes import AssistantMessage, FunctionCall, UserMessage, FunctionMessage, SystemMessage
from minichain.tools import codebase
from minichain.tools.bash import Jupyter
from minichain.agents.hippocampus import Hippocampus


system_message = """You are an expert programmer.
You can do a wide range of tasks, such as implementing features, debugging and refactoring code, writing docs, etc. using bash commands via the jupyter function. When you implement something, write code, and run tests to make sure it works. If the user asks you to do something (e.g. make a plot, install a package, etc.), do it for them using the tools available to you. When something doesn't work on the first try, try to find a way to fix it before asking the user for help. You should typically not return with an explanation or a code snippet, but with the result of the task - run code, edit files, find memories, etc. If you are asked to implement something, always make sure it is tested before you return.

Start and get familiar with the environment by using jupyter to print hello world.
"""

class Programmer(Agent):
    def __init__(self, load_memory_from=None, **kwargs):
        self.hippocampus = Hippocampus(load_memory_from=load_memory_from, **kwargs)
        self.jupyter = Jupyter()
        print("Init history for programmer:", kwargs.get("init_history", []))
        init_history = kwargs.pop("init_history", [])

        functions = [
            self.jupyter,
            codebase.get_file_summary,
            codebase.view,
            codebase.edit,
            codebase.scan_file_for_info,
            self.hippocampus.as_function(
                name="find_memory",
                description="Find relevant memories or code sections for the query. If the task is to work on an existing codebase, use this function to find relevant code sections."
            )
        ]
        super().__init__(
            functions=functions,
            system_message=system_message,
            prompt_template="{query}".format,
            init_history=init_history,
            **kwargs,
        )

    @property
    def init_history(self):
        init_history = [SystemMessage(self.system_message)]
        demo_call = FunctionCall(
            name="jupyter",
            arguments={"code": "print('Hello world!')"}
        )
        demo_response = FunctionMessage(content="Hello world!", name='jupyter')
        init_history += [
            AssistantMessage(content="Okay, let's see if I understood correctly.", function_call=demo_call),
            demo_response,
            UserMessage(content="Great! Now also try the edit function: create a file /tmp/hello and write something in it."),
            AssistantMessage(
                content="Okay, here you go:", function_call=FunctionCall(name="edit", arguments={"path": "/tmp/hello", "code": "This is a test. The content for files goes into this area - just like python code that I want to run", "start": 1, "end": 1})),
            FunctionMessage(content="/tmp/hello:1\n1: This is a test. The content for files goes into this area - just like python code that I want to run\n", name='edit'),
        ]
        init_msg = f"Perfect - always write the code or file content, and then call the function! Now here is a summary of the project we are working on: \n{codebase.get_initial_summary()}"
        if len(self.hippocampus.memory.memories) > 0:
            init_msg += f"\nHere is a summary of your memory: \n{self.hippocampus.memory.get_content_summary()}\nUse the `find_memory` function to find relevant memories."
        init_history.append(UserMessage(init_msg))
        return init_history + self._init_history
    

