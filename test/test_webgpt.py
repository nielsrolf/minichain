import pytest
from minichain.agents.webgpt import WebGPT


@pytest.mark.asyncio
async def test_webgpt():
    query = "How can I play an audio file from s3 using https://www.elementary.audio/docs in the web using the virtual filesystem?"
    result = await WebGPT().run(query=query)
    print(result["content"])
    print(result["citations"])
