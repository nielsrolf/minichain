import os
import uuid
from typing import Callable, List, Optional, Union

import docker
from pydantic import BaseModel, Field

from minichain.agent import Function
from minichain.utils.docker_sandbox import bash, run_in_container
import asyncio


class BashQuery(BaseModel):
    commands: List[str] = Field(..., description="A list of bash commands.")


async def async_print(i, final=False):
    print(i)


class BashSession(Function):
    def __init__(self, stream=async_print, image_name="nielsrolf/minichain:latest"):
        super().__init__(
            name="bash",
            openapi=BashQuery,
            function=self,
            description="Run bash commands. Each new command is run in the project root directory.",
        )
        # self.session = uuid.uuid4().hex
        self.image_name = image_name
        self.stream = stream
        self.cwd = os.getcwd()
        self.session = self.cwd.replace("/", "").replace(".", "").replace("-", "").replace("_", "").replace(" ", "")
        # start a hello world echo command because this will trigger the preinstalling of the packages
        # if we do asyncio.run, we get: RuntimeError: asyncio.run() cannot be called from a running event loop
        # so we just create a background task
        print("Starting bash session:", self.session)
        try:
            asyncio.create_task(self.__call__(commands=["echo hello world"]))
        except Exception as e:
            print(e)
        self.has_stream = True


    async def __call__(self, commands: List[str]) -> str:
        print("Using stream:", self.stream.__name__)
        outputs = await bash([f"cd {self.cwd}"] + commands + ["pwd"], session=self.session, stream=self.stream)
        self.cwd = outputs[-1].strip()
        response = "".join(outputs[2:-2])
        print("done:", commands, response)
        await self.stream(response, final=True)
        return response

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
    def __init__(self, stream=async_print, **kwargs):
        super().__init__(
            name="python",
            openapi=CodeInterpreterQuery,
            function=self,
            description="Create and run a temporary python file (non-interactively).",
        )
        self.bash = BashSession(stream=stream)
        self.has_stream = True

    async def __call__(self, code: str) -> str:
        first_lines = """import sys
import builtins
def print(*args, **kwargs):
    builtins.print(*args, **kwargs)
    sys.stdout.flush()
"""
        last_line = 'import types; print(", ".join([f"{k}: {v}" for k, v in locals().items() if not k.startswith("_") and not isinstance(v, type) and not isinstance(v, types.ModuleType) and not isinstance(v, types.FunctionType) ]))'
        code = first_lines + code + "\n" + last_line
        filename = uuid.uuid4().hex[:5]
        with open(f"{filename}.py", "w") as f:
            f.write(code)
        self.bash._register_stream(self.stream)
        output = await self.bash(commands=[f"python {filename}.py"])
        os.remove(f"{filename}.py")
        return output


async def test_bash_session():
    bash = BashSession(stream=async_print)
    # response = bash(commands=["echo hello world", "pip install librosa"])
    response = await bash(commands=["mkdir bla123", "cd bla123", "touch testfile", "echo hello world"])
    response = await bash(commands=["ls"])
    assert "testfile" in response.split("\n")
    response = await bash(commands=["pwd"])
    assert "bla123" in response
    response = await bash(commands=["cd ..", "rm -rf bla123"])


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_bash_session())
