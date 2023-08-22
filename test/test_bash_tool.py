import pytest
import asyncio

from minichain.tools.bash import BashSession


@pytest.mark.asyncio
async def test_bash_session():
    bash = BashSession(stream=lambda i: print(i, end=""))
    # response = bash(commands=["echo hello world", "pip install librosa"])
    response = await bash(commands=["touch testfile", "echo hello world"])
    assert response.split("\n")[-2] == "hello world"
    response = await bash(commands=["ls"])
    assert "testfile" in response.split("\n")
    await bash(commands=["rm testfile"])
