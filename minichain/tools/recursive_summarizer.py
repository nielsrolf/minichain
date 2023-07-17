from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from minichain.agent import Agent, Done, Function, SystemMessage
from minichain.tools.document_qa import qa_function
from minichain.tools.summarize import summarizer_function
from minichain.utils.document_splitter import split_document
from minichain.utils.markdown_browser import markdown_browser


def summarize_until_word_limit_is_okay(
    text, question=None, max_words=500, summarize_at_least_once=False
):
    if len(text.split()) < max_words and not summarize_at_least_once:
        return text
    else:
        if question is None:
            summary = summarizer_function(text=text)
        else:
            summary = qa_function(text=text, question=question)
            summary = (
                summary["content"]
                + "\nSources: "
                + "\n".join(f"[{i['id']}] {i['source']}" for i in summary["citations"])
            )
        summary = summarize_until_word_limit_is_okay(
            summary, max_words=max_words, question=question
        )
        print(len(text.split()), "->", len(summary.split()))
        return summary


class DocumentQARequest(BaseModel):
    text: str = Field(..., description="The text to summarize.")
    question: str = Field(None, description="A question to focus on a specific topic.")
    max_words: Optional[int] = Field(
        500, description="The maximum number of words in the summary."
    )


class DocumentSummaryRequest(BaseModel):
    text: str = Field(..., description="The text to summarize.")
    max_words: Optional[int] = Field(
        500, description="The maximum number of words in the summary."
    )


def recursive_summarizer(text, question=None, max_words=500, instructions=[]):
    paragraphs = split_document(text)
    summarize_at_least_once = True
    while len(paragraphs) > 1:
        # print("splitting paragraphs:", [len(i.split()) for i in paragraphs])
        summaries = [
            recursive_summarizer(
                i, max_words=max_words, question=question, instructions=instructions
            )
            for i in paragraphs
        ]
        joint_summary = "\n\n".join(summaries)
        # remove leading and trailing newlines
        summarize_at_least_once = len(summaries) > 1
        joint_summary = joint_summary.strip()
        paragraphs = split_document(joint_summary)
    return summarize_until_word_limit_is_okay(
        paragraphs[0],
        max_words=max_words,
        question=question,
        summarize_at_least_once=summarize_at_least_once,
    )


def text_scan(text, response_openapi, system_message, on_add_output=None):
    """
    Splits the text into paragraphs and asks the document_to_json agent for outouts."""
    outputs = []

    def add_output(**output):
        if on_add_output is not None:
            on_add_output(output)
        print("adding output:", output)
        if output in outputs:
            return "Error: already added."
        outputs.append(output)
        return "Output added. continue to scan the text and add relevant outputs or end the scan with the 'return' function."

    add_output_function = Function(
        name="add_output",
        openapi=response_openapi,
        function=add_output,
        description="Add an output to the list of outputs. Don't add the same item twice.",
    )

    document_to_json = Agent(
        functions=[add_output_function],
        system_message=SystemMessage(system_message),
        prompt_template="{text}".format,
        response_openapi=Done,
        keep_last_messages=20,
    )

    paragraphs = split_document(text)
    for paragraph in paragraphs:
        document_to_json.run(text=paragraph)
    return outputs


def recursive_web_summarizer(url, question=None, max_words=500):
    text = markdown_browser(url)
    if question is None:
        document_request = DocumentSummaryRequest(text=text, max_words=max_words)
    else:
        document_request = DocumentQARequest(
            text=text, question=question, max_words=max_words
        )
    return recursive_summarizer(document_request)


long_document_qa = Function(
    name="long_document_qa",
    openapi=DocumentQARequest,
    function=recursive_summarizer,
    description="Summarize a long document with focus on a specific question.",
)


long_document_summarizer = Function(
    name="long_document_summarizer",
    openapi=DocumentSummaryRequest,
    function=recursive_summarizer,
    description="Summarize a long document recursively.",
)


# question = "what was the role of russia in world war 2?"
# url = "https://en.wikipedia.org/wiki/Russia"
# url = "https://www.tagesschau.de/ausland/putin-prigoschin-gespraech-100.html"

# question = "how can i play an audio file on a public s3 bucket using elementary audio?"
# url = "https://www.elementary.audio/docs/packages/web-renderer"

# summary = recursive_web_summarizer(url, question)
# print(summary)
# print(len(summary.split()))
