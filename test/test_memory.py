from minichain.memory import SemanticParagraphMemory
from minichain.utils.markdown_browser import markdown_browser


def test_semantic_paragraph_memory():
    memory = SemanticParagraphMemory()
    url = "https://en.wikipedia.org/wiki/Python_(programming_language)"
    text = markdown_browser(url)
    memory.ingest(text, url)
    result = memory.semantic_search("What is the latest version of Python?")
    print(result)
