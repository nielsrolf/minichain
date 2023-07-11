from pydantic import BaseModel, Field

from minichain.agent import Agent, Function, FunctionMessage, SystemMessage


class SummarizeQuery(BaseModel):
    text: str = Field(..., description="The text to summarize.")


def summarize(request: SummarizeQuery):
    return _summarize(request.text)


def _summarize(text, instructions=[]):
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
    if summary.lower() == "skip":
        summary = ""
    return summary


summarizer_function = Function(
    name="summarizer",
    openapi=SummarizeQuery,
    function=summarize,
    description="Summarize the the text provided by the user.",
)
