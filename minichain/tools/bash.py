import os
import uuid
from typing import Callable, List, Optional, Union

import docker
from pydantic import BaseModel, Field

from minichain.agent import Function
from minichain.utils.docker_sandbox import bash, run_in_container


class BashQuery(BaseModel):
    commands: List[str] = Field(..., description="A list of bash commands.")


class BashSession(Function):
    def __init__(self, stream=lambda i: i, image_name="nielsrolf/minichain:latest"):
        super().__init__(
            name="bash",
            openapi=BashQuery,
            function=self,
            description="Run bash commands. Each new command is run in the project root directory.",
        )
        self.session = uuid.uuid4().hex
        self.image_name = image_name
        self.stream = stream

    async def __call__(self, commands: List[str]) -> str:
        return bash(commands, session=self.session, stream=self.stream)

    # when the session is destroyed, stop the container
    # def __del__(self):
    #     # stop the container with name self.session
    #     client = docker.from_env()
    #     try:
    #         container = client.containers.get(self.session)
    #         container.stop()
    #     except docker.errors.NotFound:
    #         pass


class CodeInterpreterQuery(BaseModel):
    code: str = Field(..., description="Python code to run.")


class CodeInterpreter(Function):
    def __init__(self, stream=lambda i: i, **kwargs):
        super().__init__(
            name="python",
            openapi=CodeInterpreterQuery,
            function=self,
            description="Create and run a temporary python file (non-interactively).",
        )
        self.bash = BashSession(stream=stream)

    async def __call__(self, code: str) -> str:
        filename = uuid.uuid4().hex
        with open(f"{filename}.py", "w") as f:
            f.write(code)
        output = self.bash(commands=[f"python {filename}.py"])
        os.remove(f"{filename}.py")
        return output


async def test_bash_session():
    bash = BashSession(stream=lambda i: print(i, end=""))
    # response = bash(commands=["echo hello world", "pip install librosa"])
    response = await bash(commands=["touch testfile", "echo hello world"])
    assert response.split("\n") == "hello world"
    response = bash(commands=["ls"])
    assert "testfile" in response.split("\n")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_bash_session())
