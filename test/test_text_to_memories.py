import pytest

from minichain.tools.text_to_memory import text_to_memory


@pytest.mark.asyncio
async def test_text_to_memory():
    example_file = "minichain/utils/docker_sandbox.py"
    with open(example_file, "r") as f:
        content = f.read()
    memories = await text_to_memory(content, source=example_file)
    print("titles", "\n".join([i.memory.title for i in memories]))
    print(memories)
