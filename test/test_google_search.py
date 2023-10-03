import pytest

from minichain.agent import Agent, SystemMessage
from minichain.tools.google_search import web_search
from minichain.tools.recursive_summarizer import long_document_qa


@pytest.mark.asyncio
async def test_google_search():
    agent = Agent(
        functions=[web_search, long_document_qa],
        system_message="Use google to search the web for a query.",
        prompt_template="{query}".format,
    )
    query = "What is the capital of France?"
    result = await agent.run(query=query)
    print(result)
