import asyncio

from pydantic import BaseModel, Field

from minichain.agent import Agent, SystemMessage, UserMessage
# from minichain.tools.code_interpreter import code_interpreter
from minichain.tools.bash import CodeInterpreter
from typing import List, Optional

from minichain.tools.replicate_client import *


models = {
    "text_to_image": "stability-ai/sdxl:d830ba5dabf8090ec0db6c10fc862c6eb1c929e1a194a5411852d25fd954ac82",
    # "text_to_video": "anotherjesse/zeroscope-v2-xl:9f747673945c62801b13b84701c783929c0ee784e4748ec062204894dda1a351",
    "text_to_music": "facebookresearch/musicgen:7a76a8258b23fae65c5a22debb8841d1d7e816b75c2f24218cd2bd8573787906",
    "image_to_text": "andreasjansson/blip-2:4b32258c42e9efd4288bb9910bc532a69727f9acd26aa08e175713a0a857a608",
    # text_to_speech: ?
    "speech_to_text": "openai/whisper:91ee9c0c3df30478510ff8c8a3a545add1ad0259ad3a9f78fba57fbc05ee64f7"
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
                "You are a multimodal AI. You use the models available to you to interact with media files. You also use the python interpreter and ffmpeg when needed."
            ),
            prompt_template="{query}".format,
            silent=silent,
            response_openapi=MultiModalResponse,
            **kwargs,
        )


