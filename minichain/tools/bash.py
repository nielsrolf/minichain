from minichain.utils.docker_sandbox import  run_in_container, bash
from minichain.agent import Function
from pydantic import BaseModel, Field
from typing import Callable, List, Optional, Union
import uuid
import docker

class BashQuery(BaseModel):
    commands: List[str] = Field(..., description="A list of bash commands.")





class BashSession(Function):
    def __init__(self, stream=lambda i: i, image_name="nielsrolf/minichain:latest"):
        super().__init__(name="bash", openapi=BashQuery, function=self, description="Run bash commands.")
        self.session = uuid.uuid4().hex
        self.image_name = image_name
        self.stream = stream

    def __call__(self, commands: List[str]) -> str:
        return bash(commands, session=self.session, stream=self.stream)
    
    # when the session is destroyed, stop the container
    def __del__(self):
        # stop the container with name self.session
        client = docker.from_env()
        try:
            container = client.containers.get(self.session)
            container.stop()
        except docker.errors.NotFound:
            pass



def test_bash_session():
    bash = BashSession(stream=lambda i: print(i, end=""))
    # response = bash(commands=["echo hello world", "pip install librosa"])
    response = bash(commands=["touch testfile", "echo hello world"])
    assert response.split("\n") == "hello world"
    response = bash(commands=["ls"])
    assert "testfile" in response.split("\n")


if __name__ == "__main__":
    test_bash_session()


    
