from pydantic import BaseModel, Field

from minichain.agent import Agent, Function, FunctionMessage, SystemMessage


class QuestionAnsweringQuery(BaseModel):
    text: str = Field(..., description="The text to scan for relevant information.")
    question: str = Field(..., description="The question to answer.")


def qa(request: QuestionAnsweringQuery):
    return _qa(request.text, request.question)

def _qa(text, question, instructions=[]):
    # system_message = f"Scan the text provided by the user for relevant information related to the question: '{question}'. Summarize long passages if needed. You may repeat sections of the text verbatim if they are very relevant. Do not start the summary with 'The text provided by the user' or similar phrases. Only respond with informative text relevant to the question. Summarize by generating a shorter text that has the most important information from the text provided by the user."
    system_message = (
        f"You are a document based QA system. Your task is to find all relevant information in the provided text related to the question: '{question}'."
        + "When working with long documents, you work in a recursive way, meaning that your previous answers / summaries are provided as input to the next iteration. If the text contains relevant information regarding the question, but this information is not sufficient to answer the question, simply summarize the relevant information. When in doubt, don't skip - in particular if the text contains information that might be useful in conjunction with text you might summarize later."
        + "You may repeat sections of the text verbatim if they are very relevant, in particular when working with code. Do not start the summary with 'The text provided' or similar phrases. Don't speak about the text ('The document contains info about' etc.), instead tell the user the information directly."
    )
    system_message += (
        "\n"
        + "Ignore parts of a website that are not content, such as navigation bars, footers, sidebars, etc. Respond only with the word 'skip' if the text consists of only these parts. If the text contains no information related to the question, also answer only with the word 'skip'."
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


qa_function = Function(
    name="document_qa",
    openapi=QuestionAnsweringQuery,
    function=qa,
    description="Scan a text for relevant information related to a question.",
)
