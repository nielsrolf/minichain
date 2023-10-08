import asyncio

from pydantic import BaseModel, Field

from minichain.agent import Agent
from minichain.dtypes import AssistantMessage, FunctionCall, UserMessage, FunctionMessage
from minichain.tools import codebase
from minichain.tools.bash import CodeInterpreter
from minichain.agents.hippocampus import Hippocampus


system_message = """You are an expert programmer.
You can do a wide range of tasks, such as implementing features, debugging and refactoring code, writing docs, etc. using bash commands. Avoid interactive commands, outputs are only send when a command finished execution. When you implement something, write code, and run tests to make sure it works. If the user asks you to do something (e.g. make a plot, install a package, etc.), do it using the bash and python functions, and explain what you did instead of responding to the user directly. When something doesn't work on the first try, try to find a way to fix it before asking the user for help.

Start and get familiar with the environment by using python to print hello world.
"""

class Programmer(Agent):
    def __init__(self, load_memory_from=None, **kwargs):
        self.hippocampus = Hippocampus(load_memory_from=load_memory_from, **kwargs)
        interpreter = CodeInterpreter()
        # bash = BashSession()
        self.interpreter = interpreter
        print("Init history for programmer:", kwargs.get("init_history", []))
        init_history = kwargs.pop("init_history", [])
        if init_history == []:
            init_history = self.get_init_history()

        functions = [
            # bash,
            interpreter,
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

    def get_init_history(self):
        init_history = []
        demo_call = FunctionCall(
            name="python",
            arguments={"code": "print('Hello world!')"}
        )
        demo_response = FunctionMessage(content="> python 98123.py\nHello world!\n", name='python')
        init_history = [
            AssistantMessage(content="Okay, let's see if I understood correctly.", function_call=demo_call),
            demo_response,
            UserMessage(content="Great! Now also try to edit tool to create a file /tmp/hello and write something in it."),
            AssistantMessage(
                content="Okay, here you go:", function_call=FunctionCall(name="edit", arguments={"path": "/tmp/hello", "code": "This is a test. The content for files goes into this area - just like python code that I want to run", "start_line": 1, "end_line": 1})),
            FunctionMessage(content="/tmp/hello:1\n1: This is a test. The content for files goes into this area - just like python code that I want to run\n", name='edit'),
        ]
        init_msg = f"Perfect - always write the code or file content, and then call the function! Now here is a summary of the project we are working on: \n{codebase.get_initial_summary()}"
        init_history.append(UserMessage(init_msg))
        return init_history
    

