from minichain.agent import (Agent, AssistantMessage, Function, FunctionCall,
                             FunctionMessage, SystemMessage, UserMessage)
from minichain.memory import SemanticParagraphMemory
from minichain.utils.markdown_browser import markdown_browser
from minichain.utils.search import google_search


def summarize(text, question=None, instructions=[]):
    system_message = f"Summarize the the text provided by the user. Do not start the summary with 'The text provided by the user' or similar phrases. Summarize by generating a shorter text that has the most important information from the text provided by the user."
    system_message += (
        "\n\n"
        + "Ignore parts of a website that are not content, such as navigation bars, footers, sidebars, etc. Respond only with the word 'skip' if the text consists of only these parts."
    )
    if instructions and len(instructions) > 0:
        system_message += "\n" + "\n".join(instructions)
    summarizer = Agent(
        functions=[],
        system_message=SystemMessage(system_message),
        prompt_template="{text}".format,
    )
    summary = summarizer.run(text=text)
    if summary.content.lower() == "skip":
        summary.content = ""
    return FunctionMessage(
        name="summarizer",
        content=summary.content,
    )


summarizer_function = Function(
    name="summarizer",
    openapi={
        "text": "string",
        # optionally provide a list of instructions on what to focus on
        "instructions": "list",
    },
    function=summarize,
    description="Summarize the the text provided by the user.",
)
