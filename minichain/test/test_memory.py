from minichain.utils.markdown_browser import markdown_browser
from minichain.memory import SemanticParagraphMemory


def test_semantic_paragraph_memory():
    memory = SemanticParagraphMemory()
    url = "https://en.wikipedia.org/wiki/Python_(programming_language)"
    text = markdown_browser(url)
    memory.ingest(text, url)
    result = memory.answer_from_memory("What is the latest version of Python?")
    print(result)
