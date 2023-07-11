from minichain.tools.text_to_memory import text_to_memory
from minichain.utils.markdown_browser import markdown_browser


def test_text_to_memory():
    url = "https://en.wikipedia.org/wiki/Python_(programming_language)"
    text = markdown_browser(url)
    memories = text_to_memory(text, source=url)
    breakpoint()
    print("titles", "\n".join([memory.title for memory in memories]))
    print(memories)
