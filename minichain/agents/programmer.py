from minichain.agent import Agent, SystemMessage
from minichain.memory import SemanticParagraphMemory
from minichain.tools.code_interpreter import code_interpreter
from minichain.tools.bash import BashSession
from minichain.tools.codebase import Codebase



memory = SemanticParagraphMemory()
codebase = Codebase()


programmer = Agent(
    functions=[
        webgpt.as_function(),
        code_interpreter,
        BashSession(),
        codebase.summarize,
        codebase.qa,
        codebase.find_symbol,
        codebase.replace_symbol,
        codebase.edit_lines,
    ],
    system_message=SystemMessage(
        "You are an expert programmer. You can do a wide range of tasks, such as implementing features, debugging and refactoring code, write docs, etc. using the tools available to you. If you need access to up-to-date docs, you can use webgpt - your colleague who researches questions on the web for you. When you implement something, write and run tests to make sure it works. "
    ),
    prompt_template="{query}".format,
    response_openapi=AnswerWithCitations,
)


