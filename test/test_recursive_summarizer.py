from minichain.tools.recursive_summarizer import (
    long_document_qa,
    long_document_summarizer,
)
from minichain.utils.markdown_browser import markdown_browser


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
