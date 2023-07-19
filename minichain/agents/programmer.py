from pydantic import BaseModel, Field

from minichain.agent import Agent, SystemMessage, UserMessage

from minichain.tools import codebase
from minichain.agents.webgpt import Query, WebGPT, scan_website_function
from minichain.memory import SemanticParagraphMemory

# from minichain.tools.code_interpreter import code_interpreter
from minichain.tools.bash import BashSession, CodeInterpreter
from minichain.tools.google_search import google_search_function

memory = SemanticParagraphMemory()


class ProgrammerResponse(BaseModel):
    final_response: str = Field(..., description="The final response to the user.")


class Brogrammer(Agent):
    def __init__(self, silent=False, function_stream=lambda i: print(i), **kwargs):
        interpreter = CodeInterpreter(stream=function_stream)

        super().__init__(
            functions=[
                # WebGPT(silent=silent).as_function("webgpt", "Research the web in order to answer a question.", Query),
                interpreter.bash,
                interpreter,
                # google_search_function,
                # scan_website_function,
                codebase.get_file_summary,
                codebase.view,
                codebase.edit,
                codebase.view_symbol,
                codebase.replace_symbol,
            ],
            system_message=SystemMessage(
                "You are an expert programmer. You can do a wide range of tasks, such as implementing features, debugging and refactoring code, writing docs, etc. using bash commands. Avoid interactive commands, outputs are only send when a command finished execution. When you implement something, write code, and run tests to make sure it works. If the user asks you to do something (e.g. make a plot, install a package, etc.), do it using the bash and python functions, and explain what you did instead of responding to the user directly. When something doesn't work on the first try, try to find a way to fix it before asking the user for help."
            ),
            prompt_template="{query}".format,
            silent=silent,
            response_openapi=ProgrammerResponse,
            init_history=kwargs.get(
                "init_history",
                [
                    UserMessage(
                        f"Here is a summary of the project we are working on: \n{codebase.get_initial_summary()}"
                    )
                ],
            ),
            **kwargs,
        )


if __name__ == "__main__":
    model = Brogrammer(silent=False)

    while query := input("# User: \n"):
        response, model = model.run(query=query, keep_session=True)
        print("# Assistant:\n", response["final_response"])
        breakpoint()
