import asyncio

from pydantic import BaseModel, Field

from minichain.agent import Agent, SystemMessage, UserMessage
from minichain.memory import SemanticParagraphMemory
from minichain.tools import codebase
from minichain.tools.bash import CodeInterpreter



class ProgrammerResponse(BaseModel):
    content: str = Field(..., description="The final response to the user.")


async def async_print(i, final=False):
    # print(i)
    pass


class Programmer(Agent):
    def __init__(self, silent=False, on_stream_message=async_print, memory=None, load_memory_from=None, **kwargs):
        self.memory = memory
        if load_memory_from:
            if not memory:
                self.memory =  SemanticParagraphMemory(use_vector_search=True, agents_kwargs=kwargs)
            self.memory.load(load_memory_from)
        interpreter = CodeInterpreter(stream=on_stream_message)
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
            # codebase.view_symbol,
            # codebase.replace_symbol,
            codebase.scan_file_for_info,
        ]
        if self.memory:
            functions += [
                self.memory.find_memory_tool(),
            ]
        super().__init__(
            functions=functions,
            system_message=SystemMessage(
                "You are an expert programmer. You can do a wide range of tasks, such as implementing features, debugging and refactoring code, writing docs, etc. using bash commands. Avoid interactive commands, outputs are only send when a command finished execution. When you implement something, write code, and run tests to make sure it works. If the user asks you to do something (e.g. make a plot, install a package, etc.), do it using the bash and python functions, and explain what you did instead of responding to the user directly. When something doesn't work on the first try, try to find a way to fix it before asking the user for help."
            ),
            prompt_template="{query}".format,
            silent=silent,
            response_openapi=ProgrammerResponse,
            init_history=init_history,
            **kwargs,
        )


async def cli():
    model = Programmer(silent=False)
    await model.on_message_send({"hello": "world"})

    query = """I have a websocket in api.py that sends the following:
{type: start, conversation_id: 123}
{...message, id: 1},
{...message, id: 2, parent: 1},
{...message, id: 3, parent: 2}
{type: start, conversation_id: 4}
{type: "start", id: 5, parent=4}
h
e
r
e

c
o
...
{...message, conversation_id: 4} # message finished
{...message, conversation_id: 123} # message finished

I need you to create a react frontend for this, which works in the following way:
- on initial load, it shows only one large input field and a send button
- on send, it sends the message to the websocket. from then on, it renders the main history, but also saves the sub-histories (messages between start: 4 and end: 4 belong to conversation 4, which is a sub conversation of message 3, which belongs to the main conversation 123.
- when a message has a sub conversation, I want the sub conversation to show on the screen"""
    response = await model.run(query=query, keep_session=True)
    print(response["content"])

    while query := input("# User: \n"):
        response, model = await model.run(query=query, keep_session=True)
        breakpoint()
        print("# Assistant:\n", response["content"])
        # I want to implement a fastapi backend that acts as an interface to an agent, for example webgpt. The API should have endpoints to send a json object that is passed to agent.run(**payload), and stream back results using the streaming callbacks

        breakpoint()


if __name__ == "__main__":
    asyncio.run(cli())
