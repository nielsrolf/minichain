from pprint import pprint

from minichain.memory import SemanticParagraphMemory
from minichain.utils.markdown_browser import markdown_browser


def print_memories(memories):
    for i in memories:
        pprint(i.dict())


url = "https://en.wikipedia.org/wiki/Python_(programming_language)"
question = "What is the latest version of Python?"


def test_question_embedding_memory():
    memory = SemanticParagraphMemory(
        use_keywords_search=False, use_content_scan_search=False
    )
    text = markdown_browser(url)
    memory.ingest(text, url)
    memories = memory.retrieve(question)
    print_memories(memories)
    print(memory.rank_or_summarize(memories, question))


def test_keyword_memory():
    memory = SemanticParagraphMemory(
        use_vector_search=False, use_content_scan_search=False
    )
    text = markdown_browser(url)
    memory.ingest(text, url)
    memories = memory.retrieve()
    print_memories(memories)
    print(memory.rank_or_summarize(memories, question))


def test_content_scan_memory():
    memory = SemanticParagraphMemory(use_keywords_search=False, use_vector_search=False)
    text = markdown_browser(url)
    memory.ingest(text, url)
    memories = memory.retrieve(question)
    print_memories(memories)
    print(memory.rank_or_summarize(memories, question))
