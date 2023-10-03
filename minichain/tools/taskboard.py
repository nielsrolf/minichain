from typing import List, Optional

from pydantic import BaseModel, Field

from minichain.functions import tool


class TasksNotDoneError(Exception):
    pass


class Task(BaseModel):
    id: Optional[int] = Field(
        None, description="The id of the task - only specify when updating a task."
    )
    description: str = Field(
        ...,
        description="The description of the task - be verbose and make sure to mention every piece of information that might be relevant to the assignee.",
    )
    status: str = Field(
        "TODO",
        description="The status of the task.",
        enum=["TODO", "IN_PROGRESS", "DONE", "BLOCKED", "CANCELED"],
    )

    comments: List[str] = []

    def __str__(self):
        result = f"#{self.id} ({self.status})\n{self.description}"
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
    return "# Tasks\n" + "\n".join([str(t) for t in board.tasks])


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
