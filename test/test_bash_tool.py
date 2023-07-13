from minichain.tools.bash import BashSession


def test_bash_session():
    bash = BashSession(stream=lambda i: print(i, end=""))
    # response = bash(commands=["echo hello world", "pip install librosa"])
    response = bash(commands=["touch testfile", "echo hello world"])
    assert response.split("\n")[-2] == "hello world"
    response = bash(commands=["ls"])
    assert "testfile" in response.split("\n")
    bash(commands=["rm testfile"])