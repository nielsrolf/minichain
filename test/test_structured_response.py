import pytest

from minichain.agent import Agent
from minichain.schemas import BashQuery


@pytest.mark.asyncio
async def test_agent():
    agent = Agent(
        functions=[],
        system_message="Return a bash command that achieves the task described by the user.",
        prompt_template="{task}".format,
        response_openapi=BashQuery,
    )
    response = await agent.run(
        task="Create a file named 'test.txt' in the current directory."
    )
    assert len(response["commands"]) == 1
