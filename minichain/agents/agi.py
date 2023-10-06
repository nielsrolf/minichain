from typing import List

from pydantic import Field

from minichain.agent import Agent, make_return_function
from minichain.agents.programmer import Programmer
from minichain.agents.replicate_multimodal import Artist, MultiModalResponse
from minichain.agents.webgpt import WebGPT
from minichain.dtypes import UserMessage, FunctionCall, FunctionMessage, AssistantMessage
from minichain.functions import tool
from minichain.schemas import MultiModalResponse
from minichain.tools import codebase, taskboard


system_message = """You are a smart and friendly AGI.
You work as a programmer - or sometimes better as a manager of programmers - and fulfill tasks for the user.
You are equipped with a wide range of tools, notably:
- a memory: you can use it to find relevant code sections and more
- a task board: you can use it to break down complex tasks into sub tasks and assign them to someone to work on
- the assign tool: you can use it to assign tasks to copies of yourself or a programmer
- some tools to work with code: you can use them to implement features, refactor code, write tests, etc.

If the user asks you something simple, do it directly.
If the user asks you something complex about the code, make a plan first:
- try to find relevant memories
- try to find relevant code sections using the view tool if needed
- once you know enough to make a plan, create tasks on the board
- assign them to someone - they will report back to you in detail. Tell them all the relevant code sections you found.
- readjust the plan as needed by updating the board
With this approach, you are able to solve complex tasks - such as implementing an entire app for the user - including making a backend (preferably with fastapi), a frontend (preferably with React), and a database (preferably with sqlite).

If you are asked to implement something, always make sure it is tested before you return.

The user is lazy, don't ask them questions, don't explain them how they can do things, and don't just make plans - instead, just do things for them.

Start and get familiar with the environment by using python to get the current time.
"""


class AGI(Agent):
    """
    AGI is a GPT agent with access to all the tools.
    """

    def __init__(self, **kwargs):
        self.board = taskboard.TaskBoard()
        self.programmer = Programmer(**kwargs)
        self.memory = self.programmer.hippocampus.memory
        kwargs.pop("load_memory_from", None)
        self.webgpt = WebGPT(**kwargs)
        self.artist = Artist(**kwargs)

        @tool()
        async def assign(
            task_id: int = Field(..., description="The id of the task to assign."),
            assignee: str = Field(
                "programmer",
                description="The name of the assignee.",
                enum=["programmer", "copy-of-self", "artist"],
                # enum=["programmer", "webgpt", "copy-of-self", "artist"],
            ),
            relevant_code: List[str] = Field(
                [],
                description="A list of relevant code sections in format 'path/to/file.py:start_line-end_line'",
            ),
            additional_info: str = Field(
                "", description="Additional message to the programmer."
            ),
        ):
            """Assign a task to an agent (copy-of-self: for complex tasks with sub tasks, programmer: to work on the codebase, webgpt (rarely): to research something on the web). The assignee will immediately start working on the task."""
            task = [i for i in self.board.tasks if i.id == task_id][0]
            board_before = await taskboard.update_status(
                self.board, task_id, "IN_PROGRESS"
            )
            query = (
                f"Please work on the following ticket: \n{str(task)}\n{additional_info}\nThe ticket is already assigned to you and set to 'IN_PROGRESS'.\n"
                "When you are done, return with a detailed explanation of what you did, including a list of all the files you changed and an explanation of how to test and use the new feature.\n"
            )
            if len(relevant_code) > 0:
                code_context = "\n".join(relevant_code)
                query += f"Here is some relevant code:\n{code_context}"
            if "programmer" in assignee.lower():
                self.programmer.register_stream(self.stream)
                response = await self.programmer.run(
                    query=query,
                )
            elif "webgpt" in assignee.lower():
                response = await self.webgpt.run(
                    query=f"Please research on the following ticket:\n{task.description}\n{additional_info}",
                )
            elif "copy-of-self" in assignee.lower():
                response = await self.run(
                    query=query,
                )
            elif "artist" in assignee.lower():
                response = await self.artist.run(
                    query=f"Please research on the following ticket:\n{task.description}\n{additional_info}",
                )
            else:
                return f"Error: Unknown assignee: {assignee}"
            
            response = response['content']
            board_after = await taskboard.get_board(self.board)

            if board_before != board_after:
                response += f"\nHere is the updated task board:\n{board_after}"

            info_to_memorize = (
                f"{assignee} worked on the following ticket:\n{task.description}\n{additional_info}. \n"
                f"Here is the response:\n{response}"
            )
            source = f"Task: {task.description}"
            await self.memory.add_single_memory(
                content=info_to_memorize,
                source=source,
                watch_source=False,
                scope=self.stream.conversation_stack[-2]
            )
            return response

        assign.manager = self


        def check_board(**arguments):
            """Checks if there are still tasks not done on the board"""
            todo_tasks = [
                i for i in self.board.tasks if i.status in ["TODO", "IN_PROGRESS"]
            ]
            if len(todo_tasks) > 0:
                raise taskboard.TasksNotDoneError(
                    f"There are still {len(todo_tasks)} tasks not done on the board. Please finish them first."
                )

        return_function = make_return_function(MultiModalResponse, check_board)

        board_tools = taskboard.tools(self.board)
        all_tools = self.programmer.functions + board_tools
        tools_dict = {i.name: i for i in all_tools}
        tools_dict.pop("return")
        all_tools = list(tools_dict.values()) + [assign, return_function]

        init_history = kwargs.pop("init_history", [])
        if init_history == []:
            init_history = self.get_init_history()

        super().__init__(
            functions=all_tools,
            system_message=system_message,
            prompt_template="{query}".format,
            response_openapi=MultiModalResponse,
            init_history=init_history,
            **kwargs,
        )

    def get_init_history(self):
        init_history = []
        demo_call = FunctionCall(
            name="python",
            arguments={"code": "print('Hello world!')"}
        )
        demo_response = FunctionMessage("> python 98123.py\nHello world!\n", name='python')
        init_history = [
            AssistantMessage(content="Okay, let's see if I understood correctly.", function_call=demo_call),
            demo_response,
            UserMessage(content="Great! Now also try to edit tool to create a file /tmp/hello and write something in it."),
            AssistantMessage(
                content="Okay, here you go:", function_call=FunctionCall(name="edit", arguments={"path": "/tmp/hello", "code": "This is a test. The content for files goes into this area - just like python code that I want to run", "start_line": 1, "end_line": 1})),
            FunctionMessage("/tmp/hello:1\n1: This is a test. The content for files goes into this area - just like python code that I want to run\n", name='edit'),
        ]
        init_msg = f"Perfect - always write the code or file content, and then call the function! Now here is a summary of the project we are working on: \n{codebase.get_initial_summary()}"
        if self.memory and len(self.memory.memories) > 0:
            init_msg += f"\nHere is a summary of your memory: \n{self.memory.get_content_summary()}\nUse the `find_memory` function to find relevant memories."
        init_history.append(UserMessage(init_msg))
        return init_history
    

