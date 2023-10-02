import pytest

from minichain.agents.webgpt import WebGPT


@pytest.mark.asyncio
async def test_webgpt():
    # query = "How can I play an audio file from s3 using https://www.elementary.audio/docs in the web using the virtual filesystem?"
    # query = "what is the first search result when you search for 'agi has been achieved by function calls'?"
    query = "give me a 2-sentence summary of https://raw.githubusercontent.com/nielsrolf/thoughts/main/unit_of_consciousness.md"
    result = await WebGPT().run(query=query)
    print(result["content"])
    print(result["citations"])
