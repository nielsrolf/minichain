import asyncio
import os
import uuid
from typing import Callable, List, Optional, Union
import json

import docker
from pydantic import BaseModel, Field

from minichain.agent import Function
from minichain.utils.docker_sandbox import bash, run_in_container


class BashQuery(BaseModel):
    commands: List[str] = Field(..., description="A list of bash commands.")
    timeout: Optional[int] = Field(60, description="The timeout in seconds.")


async def async_print(i, final=False):
    # print(i)
    pass


def shorten_response(response: str) -> str:
    # remove character in each line after the first 100 characters, add ... if the line is longer
    response = "\n".join(
        [
            line[:200] + ("..." if len(line) > 200 else "")
            for line in response.split("\n")
        ]
    )
    # if more than 100 lines, remove all lines except the first 5 and the last 5 and insert ...
    lines = response.split("\n")
    if len(lines) > 100:
        response = "\n".join(lines[:20] + ["..."] + lines[-80:])
    return response


class BashSession(Function):
    def __init__(self, stream=async_print, image_name="nielsrolf/minichain:latest"):
        super().__init__(
            name="bash",
            openapi=BashQuery,
            function=self,
            description="Run bash commands. Cwd is reset after each message. Run commands with the -y flag to avoid interactive prompts (e.g. npx create-app)",
        )
        # self.session = uuid.uuid4().hex
        self.image_name = image_name
        self.stream = stream
        self.cwd = os.getcwd()
        self.session = (
            self.cwd.replace("/", "")
            .replace(".", "")
            .replace("-", "")
            .replace("_", "")
            .replace(" ", "")
        )
        # start a hello world echo command because this will trigger the preinstalling of the packages
        # if we do asyncio.run, we get: RuntimeError: asyncio.run() cannot be called from a running event loop
        # so we just create a background task
        print("Starting bash session:", self.session)
        try:
            asyncio.create_task(self.__call__(commands=["echo hello world"]))
        except Exception as e:
            print(e)
        self.has_stream = True

    async def __call__(self, commands: List[str], timeout: int = 60) -> str:
        print("Using stream:", self.stream.__name__)
        await bash([f"cd {self.cwd}"], session=self.session)
        if any(["npx" in i for i in commands]):
            timeout = max(timeout, 180)
        outputs = await bash(
            commands,
            session=self.session,
            stream=self.stream,
            timeout=timeout,
        )
        response = "".join(outputs)
        response = shorten_response(response)
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
    code: str = Field(..., description="Python code to run. Code can also be passed directly as a string without the surrounding 'code' field. ")
    timeout: Optional[int] = Field(60, description="The timeout in seconds.")


first_lines = """import sys
import builtins
def print(*args, **kwargs):
    builtins.print(*args, **kwargs)
    sys.stdout.flush()
"""

last_lines = """import types
print(", ".join([f"{k}: {v}" for k, v in locals().items() if k in <lastLine> ]))"""

class CodeInterpreter(Function):
    def __init__(self, stream=async_print, **kwargs):
        super().__init__(
            name="python",
            openapi=CodeInterpreterQuery,
            function=self,
            description="Create and run a temporary python file (non-interactively; jupyter-style !bash commands are not supported).",
        )
        self.bash = BashSession(stream=stream)
        self.has_stream = True

    async def __call__(self, code: str, timeout: int = 60) -> str:
        last_line = json.dumps(code.strip().split("\n")[-1])
        code = first_lines + code
        if not "=" in last_line and not "plt" in last_line and not "print" in last_line and not "import" in last_line and not "save" in last_line and not last_line.startswith("#"):
            code = code + "\n" + last_lines.replace("<lastLine>", last_line)
        filename = uuid.uuid4().hex[:5]
        filepath = f"{self.bash.cwd}/.minichain/{filename}.py"
        with open(filepath, "w") as f:
            f.write(code)
        self.bash._register_stream(self.stream)
        output = await self.bash(commands=[f"python {filepath}"], timeout=timeout)
        return output


async def test_bash_session():
    bash = BashSession(stream=async_print)
    # response = bash(commands=["echo hello world", "pip install librosa"])
    response = await bash(
        commands=["mkdir bla123", "cd bla123", "touch testfile", "echo hello world"]
    )
    response = await bash(commands=["ls"])
    assert "testfile" in response.split("\n")
    response = await bash(commands=["pwd"])
    assert "bla123" in response
    response = await bash(commands=["cd ..", "rm -rf bla123"])


if __name__ == "__main__":
    import asyncio

    asyncio.run(test_bash_session())
