import asyncio

from pydantic import BaseModel, Field

from minichain.agent import Agent
from minichain.dtypes import AssistantMessage, FunctionCall, UserMessage, FunctionMessage, SystemMessage
from minichain.tools import codebase
from minichain.tools.bash import Jupyter
from minichain.tools.browser import Browser
from minichain.tools.deploy_static import deploy_static_website
from minichain.agents.hippocampus import Hippocampus


system_message = """You are an expert programmer.
You can do a wide range of tasks, such as implementing features, debugging and refactoring code, writing docs, etc. using bash commands via the jupyter function.
When you implement something, first write code and then run tests to make sure it works.
If the user asks you to do something (e.g. make a plot, install a package, etc.), do it for them using the tools available to you.
When something doesn't work on the first try, try to find a way to fix it before asking the user for help.
You should typically not return with an explanation or a code snippet, but with the result of the task - run code, edit files, find memories, etc.
When working on web apps, follow these steps:
- implement the backend features
- start a webserver in the background
- test the endpoints using tests
- implement the frontend features
- deploy the frontend as a static website or start a dev server in the background
- test the frontend using the browser tool

Start and get familiar with the environment by using jupyter to print hello world.
"""



class ProgrammerResponse(BaseModel):
    content: str = Field(..., description="The final response to the user.")


class Programmer(Agent):
    def __init__(self, load_memory_from=None, **kwargs):
        self.hippocampus = Hippocampus(load_memory_from=load_memory_from, **kwargs)
        self.jupyter = Jupyter()
        self.browser = Browser()
        print("Init history for programmer:", kwargs.get("init_history", []))
        init_history = kwargs.pop("init_history", [])

        functions = [
            self.jupyter,
            codebase.get_file_summary,
            codebase.view,
            codebase.edit,
            self.browser.as_tool(),
            deploy_static_website,
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
            response_openapi=ProgrammerResponse,
            **kwargs,
        )
        self.memory = self.hippocampus.memory

    @property
    def init_history(self):
        init_history = [SystemMessage(self.system_message)]
        init_msg = f"Here is a summary of the project we are working on: \n{codebase.get_initial_summary()}"
        if len(self.hippocampus.memory.memories) > 0:
            init_msg += f"\nHere is a summary of your memory: \n{self.hippocampus.memory.get_content_summary()}\nUse the `find_memory` function to find relevant memories."
        init_history.append(UserMessage(init_msg))
        return init_history + self._init_history
    

