import asyncio
import os
from typing import List, Optional

from pydantic import BaseModel, Field

from minichain.agent import Function
from minichain.schemas import BashQuery
from minichain.utils.docker_sandbox import bash


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
    def __init__(self, message_handler=None, image_name="nielsrolf/minichain:latest"):
        super().__init__(
            name="bash",
            openapi=BashQuery,
            function=self,
            description="Run bash commands. Cwd is reset after each message. Run commands with the -y flag to avoid interactive prompts (e.g. npx create-app)",
            message_handler=message_handler,
        )
        # self.session = uuid.uuid4().hex
        self.image_name = image_name
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

    async def __call__(self, commands: List[str], timeout: int = 60, **ignored_kwargs) -> str:
        await bash([f"cd {self.cwd}"], session=self.session)
        if any(["npx" in i for i in commands]):
            timeout = max(timeout, 180)
        outputs = await bash(
            commands,
            session=self.session,
            stream=self.message_handler,
            timeout=timeout,
        )
        response = "".join(outputs)
        response = shorten_response(response)
        print("done:", commands, response)
        await self.message_handler.set({"content": response})
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
    code: str = Field(
        ...,
        description="Python code to run",
    )
    timeout: Optional[int] = Field(60, description="The timeout in seconds.")


first_lines = """import sys
import builtins
def print(*args, **kwargs):
    builtins.print(*args, **kwargs)
    sys.stdout.flush()
"""

last_lines = """import types
print(", ".join([f"{k}: {v}" for k, v in locals().items() if k in <lastLine> ]))"""

import nbformat as nbf
from nbconvert.preprocessors import ExecutePreprocessor

class CodeInterpreter(Function):
    def __init__(self, message_handler=None, **kwargs):
        super().__init__(
            name="python",
            openapi=CodeInterpreterQuery,
            function=self,
            description="Create and run a temporary python file (non-interactively; jupyter-style !bash commands are not supported).",
            message_handler=message_handler,
        )
        self.notebook = nbf.v4.new_notebook()
        self.ep = ExecutePreprocessor(timeout=600, kernel_name='python3')

    async def __call__(self, code: str, timeout: int = 60) -> str:
        breakpoint()
        new_cell = nbf.v4.new_code_cell(code)
        self.notebook.cells.append(new_cell)
        self.ep.preprocess(self.notebook, {'metadata': {'path': '/'}})
        output = self.notebook.cells[-1].outputs[0].text
        return output


async def test_bash_session():
    bash = BashSession()
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
