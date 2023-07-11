from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field

from minichain.agent import Function
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
        return summarize_until_word_limit_is_okay(summary, max_words=max_words, question=question)


class DocumentQARequest(BaseModel):
    text: str = Field(..., description="The text to summarize.")
    question: str = Field(
        None, description="A question to focus on a specific topic."
    )
    max_words: Optional[int] = Field(
        500, description="The maximum number of words in the summary."
    )


class DocumentSummaryRequest(BaseModel):
    text: str = Field(..., description="The text to summarize.")
    max_words: Optional[int] = Field(
        500, description="The maximum number of words in the summary."
    )


def recursive_summarizer(document_request: Union[DocumentQARequest,DocumentSummaryRequest]):
    return _recursive_summarizer(
        document_request.text,
        question=document_request.question if isinstance(document_request, DocumentQARequest) else None,
        max_words=document_request.max_words,
    )


def _recursive_summarizer(text, question=None, max_words=500):
    paragraphs = split_document(text)
    summarize_at_least_once = True
    while len(paragraphs) > 1:
        # print("splitting paragraphs:", [len(i.split()) for i in paragraphs])
        summaries = [
            _recursive_summarizer(i, max_words=max_words, question=question)
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


def recursive_web_summarizer(url, question=None, max_words=500):
    text = markdown_browser(url)
    if question is None:
        document_request = DocumentSummaryRequest(text=text, max_words=max_words)
    else:
        document_request = DocumentQARequest(text=text, question=question, max_words=max_words)
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

def test_long_document_qa():
    question = "what was the role of russia in world war 2?"
    url = "https://en.wikipedia.org/wiki/Russia"
    text = markdown_browser(url)
    result = long_document_qa(text=text, question=question)
    print(result)


def test_long_document_summarizer():
    url = "https://en.wikipedia.org/wiki/Russia"
    text = markdown_browser(url)
    result = long_document_summarizer(text=text)
    print(result)


if __name__ == "__main__":
    test_long_document_qa()
    print("-"*80)
    test_long_document_summarizer()


# question = "what was the role of russia in world war 2?"
# url = "https://en.wikipedia.org/wiki/Russia"
# url = "https://www.tagesschau.de/ausland/putin-prigoschin-gespraech-100.html"

# question = "how can i play an audio file on a public s3 bucket using elementary audio?"
# url = "https://www.elementary.audio/docs/packages/web-renderer"

# summary = recursive_web_summarizer(url, question)
# print(summary)
# print(len(summary.split()))
