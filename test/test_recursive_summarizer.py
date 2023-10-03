import pytest

from minichain.tools.recursive_summarizer import (
    long_document_qa,
    long_document_summarizer,
)
from minichain.utils.markdown_browser import markdown_browser


@pytest.mark.asyncio
async def test_long_document_qa():
    question = "what was the role of russia in world war 2?"
    url = "https://en.wikipedia.org/wiki/Russia"
    text = await markdown_browser(url)
    result = await long_document_qa(text=text, question=question)
    print(result)


@pytest.mark.asyncio
async def test_long_document_summarizer():
    url = "https://en.wikipedia.org/wiki/Russia"
    text = await markdown_browser(url)
    result = await long_document_summarizer(text=text)
    print(result)
