from pprint import pprint

import pytest

from minichain.memory import SemanticParagraphMemory
from minichain.utils.markdown_browser import markdown_browser


def print_memories(memories):
    for i in memories:
        pprint(i.dict())


example_file = "minichain/utils/docker_sandbox.py"
with open(example_file, "r") as f:
    text = f.read()
question = "In which line is the docker container started?"


@pytest.mark.asyncio
async def test_question_embedding_memory():
    memory = SemanticParagraphMemory(
        use_vector_search=True, use_content_scan_search=False
    )
    await memory.ingest(text, example_file)
    memories = await memory.retrieve(question)
    print_memories(memories)
    answer = await memory.rank_or_summarize(memories, question)
    print(answer)


@pytest.mark.asyncio
async def test_content_scan_memory():
    memory = SemanticParagraphMemory(
        use_vector_search=False, use_content_scan_search=True
    )
    await memory.ingest(text, example_file)
    memories = await memory.retrieve(question)
    print_memories(memories)
    answer = await memory.rank_or_summarize(memories, question)
    print(answer)
