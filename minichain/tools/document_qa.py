from typing import List, Optional

from pydantic import BaseModel, Field

from minichain.agent import Agent, Function, FunctionMessage, SystemMessage



class Citation(BaseModel):
    id: int = Field(
        ...,
        description="The number that was used in the answer to reference the citation.",
    )
    source: str = Field(..., description="The url of the citation.")


class AnswerWithCitations(BaseModel):
    content: str = Field(..., description="The answer to the question.")
    citations: Optional[List[Citation]] = Field(
        default_factory=list, description="A list of citations."
    )

    def __str__(self):
        repr = self.content
        if self.citations:
            repr += "\nSources: "
            repr += "\n".join(f"[{i.id}] {i.source}" for i in self.citations)
        return repr


async def qa(text, question, instructions=[]):
    """
    Returns: a dict {content: str, citations: List[Citation]}}"""
    # system_message = f"Scan the text provided by the user for relevant information related to the question: '{question}'. Summarize long passages if needed. You may repeat sections of the text verbatim if they are very relevant. Do not start the summary with 'The text provided by the user' or similar phrases. Only respond with informative text relevant to the question. Summarize by generating a shorter text that has the most important information from the text provided by the user."
    system_message = (
        f"You are a document based QA system. Your task is to find all relevant information in the provided text related to the question: '{question}'.\n"
        + "When working with long documents, you work in a recursive way, meaning that your previous answers / summaries are provided as input to the next iteration. If the text contains relevant information regarding the question, but this information is not sufficient to answer the question, simply summarize the relevant information. When in doubt, don't skip - in particular if the text contains information that might be useful in conjunction with text you might summarize later.\n"
        + "You may repeat sections of the text verbatim if they are very relevant, in particular when working with code. Do not start the summary with 'The text provided' or similar phrases. Don't speak about the text ('The document contains info about' etc.), instead tell the user the information directly. \n"
        + f"Question: {question}\n"
    )
    system_message += (
        "\n"
        + "Ignore parts of a website that are not content, such as navigation bars, footers, sidebars, etc. Respond only with the word 'skip' if the text consists of only these parts. If the text contains no information related to the question, also answer only with the word 'skip'.\n"
        + "If a source link is mentioned, please cite the url of the source."
    )
    if instructions and len(instructions) > 0:
        system_message += "\n" + "\n".join(instructions)
    summarizer = Agent(
        functions=[],
        system_message=SystemMessage(system_message),
        prompt_template="{text}".format,
        response_openapi=AnswerWithCitations,
    )
    summary = await summarizer.run(text=text)
    if summary["content"].lower() == "skip":
        summary["content"] = ""
    return summary
