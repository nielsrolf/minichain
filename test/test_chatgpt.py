import pytest

from minichain.agents.chatgpt import ChatGPT


@pytest.mark.asyncio
async def test_chatgpt():
    # query = "How can I play an audio file from s3 using https://www.elementary.audio/docs in the web using the virtual filesystem?"
    # query = "what is the first search result when you search for 'agi has been achieved by function calls'?"
    query = "I think people should respect all sentient beings, including animals and artificial sentience."
    result = await ChatGPT().run(query=query)
    print(result["content"])
