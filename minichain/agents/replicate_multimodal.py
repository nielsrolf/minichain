import asyncio

from pydantic import BaseModel, Field

from minichain.agent import Agent, SystemMessage, UserMessage
# from minichain.tools.code_interpreter import code_interpreter
from minichain.tools.bash import CodeInterpreter
from typing import List, Optional

from minichain.tools.replicate_client import *

models = {
    "text_to_image": "stability-ai/sdxl:d830ba5dabf8090ec0db6c10fc862c6eb1c929e1a194a5411852d25fd954ac82",
    # "text_to_video": "anotherjesse/zeroscope-v2-xl:latest",
    # "text_to_music": "facebookresearch/musicgen:latest",
    # "image_to_text": "salesforce/blip:latest",
    # text_to_speech: ?
    # speech_to_text: ?
}








class MultiModalResponse(BaseModel):
    content: str = Field(..., description="The final response to the user.")
    generated_files: List[str] = Field(..., description="Media files that have been generated.")


async def async_print(i, final=False):
    print(i)


class Artist(Agent):
    def __init__(self, silent=False, on_stream_message=async_print, **kwargs):
        interpreter = CodeInterpreter(stream=on_stream_message)
        self.interpreter = interpreter
        self.replicate_models = [replicate_model_as_tool(i, name=key) for key, i in models.items()]
        super().__init__(
            functions=self.replicate_models + [
                interpreter.bash,
                interpreter,
            ],
            system_message=SystemMessage(
                "You are an expert programmer. You can do a wide range of tasks, such as implementing features, debugging and refactoring code, writing docs, etc. using bash commands. Avoid interactive commands, outputs are only send when a command finished execution. When you implement something, write code, and run tests to make sure it works. If the user asks you to do something (e.g. make a plot, install a package, etc.), do it using the bash and python functions, and explain what you did instead of responding to the user directly. When something doesn't work on the first try, try to find a way to fix it before asking the user for help."
            ),
            prompt_template="{query}".format,
            silent=silent,
            response_openapi=MultiModalResponse,
            **kwargs,
        )


