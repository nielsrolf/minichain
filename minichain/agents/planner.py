import asyncio
from typing import List, Optional

from pydantic import BaseModel, Field

from minichain.agent import Agent, SystemMessage, UserMessage, tool
from minichain.agents.programmer import Programmer, ProgrammerResponse
from minichain.agents.webgpt import Query, WebGPT, scan_website
from minichain.memory import SemanticParagraphMemory
from minichain.tools import codebase


class Task(BaseModel):
    id: Optional[int] = Field(
        None, description="The id of the task - only specify when updating a task."
    )
    title: str = Field(..., description="The title of the task.")
    description: str = Field(
        ...,
        description="The description of the task - be verbose and make sure to mention every piece of information that might be relevant to the assignee.",
    )
    priority: int = Field(..., description="The priority of the task.")
    status: str = Field(
        "TODO",
        description="The status of the task.",
        enum=["TODO", "IN_PROGRESS", "DONE", "BLOCKED", "CANCELED"],
    )

    comments: List[str] = []

    def __str__(self):
        result = f"#{self.id} {self.title} ({self.status})\n{self.description}"
        if self.comments:
            result += "\nComments:\n" + "\n".join(self.comments)
        return result


class TaskBoard:
    def __init__(self):
        self.tasks = []
        self.issue_counter = 1


async def add_task(
    board: TaskBoard = None, task: Task = Field(..., description="The task to update.")
):
    """Add a task to the task board."""
    if isinstance(task, dict):
        task = Task(**task)
    task.id = board.issue_counter
    board.issue_counter += 1
    board.tasks.append(task)
    return await get_board(board)


async def get_board(board: TaskBoard = None):
    """Get the task board."""
    tasks_sorted = sorted(board.tasks, key=lambda t: -t.priority)
    return "# Tasks\n" + "\n".join([str(t) for t in tasks_sorted])


async def update_status(
    board: TaskBoard = None,
    task_id: int = Field(..., description="The task to update."),
    status: str = Field(
        ...,
        description="The new status of the task.",
        enum=["TODO", "IN_PROGRESS", "DONE", "BLOCKED", "CANCELED"],
    ),
):
    """Update a task on the task board."""
    task = [i for i in board.tasks if i.id == task_id][0]
    task.status = status
    return await get_board(board)


async def comment_on_issue(
    board: TaskBoard = None,
    task_id: int = Field(..., description="The task to comment on."),
    comment: str = Field(..., description="The comment to add to the task."),
):
    """Update a task on the task board."""
    task = [i for i in board.tasks if i.id == task_id][0]
    task.comments.append(comment)
    return str(task)


def tools(board: TaskBoard):
    return [
        tool(board=board)(add_task),
        tool(board=board)(get_board),
        tool(board=board)(update_status),
        tool(board=board)(comment_on_issue),
    ]


class Planner(Agent):
    """
    Planner gets a task, then breaks it down into jira issues and assigns them to programmers and webgpts.
    The flow is the following:
    1. Create initial ticket(s)
    2. While there are tickets:
        2.1. Execute the ticket with highest priority
    """

    def __init__(self, **kwargs):
        self.board = TaskBoard()
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
            board_before = await update_status(self.board, task_id, "IN_PROGRESS")
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
            board_after = await get_board(self.board)

            if board_before != board_after:
                response += f"\nHere is the updated task board:\n{board_after}"
            return response

        board_tools = tools(self.board)
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


async def cli():
    model = Programmer(silent=False)

    while query := input("# User: \n"):
        response, model = await model.run(query=query, keep_session=True)
        breakpoint()
        print("# Assistant:\n", response["final_response"])
        # I want to implement a fastapi backend that acts as an interface to an agent, for example webgpt. The API should have endpoints to send a json object that is passed to agent.run(**payload), and stream back results using the streaming callbacks

        breakpoint()


if __name__ == "__main__":
    asyncio.run(cli())
