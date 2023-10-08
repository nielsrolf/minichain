# import pytest

# from minichain.tools.bash import BashSession


# @pytest.mark.asyncio
# async def test_bash_session():
#     bash = BashSession()
#     # response = bash(commands=["echo hello world", "pip install librosa"])
#     breakpoint()
#     response = await bash(commands=["touch testfile", "echo hello world"])
#     assert "hello world" in response.split("\n")
#     response = await bash(commands=["ls"])
#     assert "testfile" in response.split("\n")
#     await bash(commands=["rm testfile"])
