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
        codebase.summarize, # Should be called in the first step and provide general context about the codebase
        codebase.qa, # Can be asked in the second step to find the right file
        codebase.find_symbol, # Can be asked in the next step to get the type description etc of a symbol
        codebase.replace_symbol, # Edit the codebase - full symbol replacement avoids errors due to wrong start and end positions
        codebase.edit_lines, # Edit the codebase - line replacement if the section is not part of a symbol or the symbol is too large
    ],
    system_message=SystemMessage(
        "You are an expert programmer. You can do a wide range of tasks, such as implementing features, debugging and refactoring code, write docs, etc. using the tools available to you. If you need access to up-to-date docs, you can use webgpt - your colleague who researches questions on the web for you. When you implement something, write and run tests to make sure it works. "
    ),
    prompt_template="{query}".format,
)


