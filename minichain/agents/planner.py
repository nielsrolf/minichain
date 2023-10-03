from pydantic import Field

from minichain.agent import Agent, SystemMessage, UserMessage, tool
from minichain.agents.programmer import Programmer, ProgrammerResponse
from minichain.agents.webgpt import WebGPT
from minichain.tools import codebase, taskboard


class Planner(Agent):
    """
    Planner gets a task, then breaks it down into jira issues and assigns them to programmers and webgpts.
    The flow is the following:
    1. Create initial ticket(s)
    2. While there are tickets:
        2.1. Execute the ticket with highest priority
    """

    def __init__(self, **kwargs):
        self.board = taskboard.TaskBoard()
        self.programmer = Programmer(**kwargs)
        self.webgpt = WebGPT(**kwargs)

        @tool()
        async def assign(
            task_id: int = Field(..., description="The id of the task to assign."),
            assignee: str = Field(
                "programmer",
                description="The name of the assignee.",
                enum=["programmer", "webgpt"],
            ),
            additional_info: str = Field(
                "", description="Additional message to the programmer."
            ),
        ):
            """Assign a task to a programmer or webgpt. The assignee will immediately start working on the task."""
            self.programmer.on_message_send = self.on_message_send
            self.webgpt.on_message_send = self.on_message_send
            task = [i for i in self.board.tasks if i.id == task_id][0]
            board_before = await taskboard.update_status(
                self.board, task_id, "IN_PROGRESS"
            )
            if "programmer" in assignee.lower():
                response = await self.programmer.run(
                    query=f"Please work on the following ticket: \n{str(task)}\n{additional_info}\nThe ticket is already assigned to you and set to 'IN_PROGRESS'.",
                )
            elif "webgpt" in assignee.lower():
                response = await self.webgpt.run(
                    query=f"Please research on the following ticket: {task.title}.\n{task.description}\n{additional_info}",
                )
            else:
                return f"Error: Unknown assignee: {assignee}"
            board_after = await taskboard.get_board(self.board)

            if board_before != board_after:
                response += f"\nHere is the updated task board:\n{board_after}"
            return response

        board_tools = taskboard.tools(self.board)
        self.programmer.functions += board_tools
        init_history = kwargs.pop("init_history", [])
        if init_history == []:
            init_history.append(
                UserMessage(
                    f"Here is a summary of the project we are working on: \n{codebase.get_initial_summary()}"
                )
            )
        super().__init__(
            functions=[
                assign,
            ]
            + board_tools,
            system_message=SystemMessage(
                "You manage a team of programmers and webgpts. When the user asks you to do something, you first create jira issues for the individual tasks. Then you assign the first task that should be done to a programmer or webgpt by calling the respective functions. When the task is done, you update the task board and assign the next task."
            ),
            prompt_template="{query}".format,
            response_openapi=ProgrammerResponse,
            init_history=init_history,
            **kwargs,
        )
