from pydantic import Field

from minichain.agent import Agent, SystemMessage, UserMessage, tool
from minichain.agents.programmer import Programmer
from minichain.agents.webgpt import WebGPT
from minichain.agents.replicate_multimodal import Artist, MultiModalResponse
from minichain.tools import codebase
from minichain.tools import taskboard


class AGI(Agent):
    """
    AGI is a GPT agent with access to all the tools.
    """

    def __init__(self, **kwargs):
        self.board = taskboard.TaskBoard()
        self.programmer = Programmer(**kwargs)
        self.webgpt = WebGPT(**kwargs)
        self.artist = Artist(**kwargs)

        @tool()
        async def assign(
            task_id: int = Field(..., description="The id of the task to assign."),
            assignee: str = Field(
                "programmer",
                description="The name of the assignee.",
                enum=["programmer", "webgpt", "copy-of-self", "artist"],
            ),
            additional_info: str = Field(
                "", description="Additional message to the programmer."
            ),
        ):
            """Assign a task to a programmer or webgpt. The assignee will immediately start working on the task."""
            self.programmer.on_message_send = self.on_message_send
            self.webgpt.on_message_send = self.on_message_send
            task = [i for i in self.board.tasks if i.id == task_id][0]
            board_before = await taskboard.update_status(self.board, task_id, "IN_PROGRESS")
            if "programmer" in assignee.lower():
                response = await self.programmer.run(
                    query=f"Please work on the following ticket: \n{str(task)}\n{additional_info}\nThe ticket is already assigned to you and set to 'IN_PROGRESS'.",
                )
            elif "webgpt" in assignee.lower():
                response = await self.webgpt.run(
                    query=f"Please research on the following ticket: {task.title}.\n{task.description}\n{additional_info}",
                )
            elif "copy-of-self" in assignee.lower():
                response = await self.run(
                    query=f"Please research on the following ticket: {task.title}.\n{task.description}\n{additional_info}",
                )
            elif "artist" in assignee.lower():
                response = await self.artist.run(
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
        all_tools = self.programmer.functions + self.artist.functions + self.webgpt.functions
        # deduplicate by name
        all_tools = list({i.name: i for i in all_tools}.values())

        init_history = kwargs.pop("init_history", [])
        if init_history == []:
            init_history.append(
                UserMessage(
                    f"Here is a summary of the project we are working on: \n{codebase.get_initial_summary()}"
                )
            )
        super().__init__(
            functions=all_tools,
            system_message=SystemMessage(
                "You are a smart and friendly AGI. You fulfill tasks for the user by using the tools available to you. If a task is complex, you break it down into sub tasks using the issue board and assign them to someone to work on. The user is lazy, don't ask them questions, don't explain them how they can do things, and don't just make plans - instead, just do things for them. If a user asks something very complex - take it as a challenge and don't stop until it is solved or proven to be unsolveable."
            ),
            prompt_template="{query}".format,
            response_openapi=MultiModalResponse,
            init_history=init_history,
            **kwargs,
        )
