from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field

from minichain.agent import Agent, Function, FunctionMessage, SystemMessage
from minichain.memory import SemanticParagraphMemory
from minichain.tools.document_qa import AnswerWithCitations
from minichain.tools.google_search import google_search_function

memory = SemanticParagraphMemory()


webgpt = Agent(
    functions=[google_search_function, memory.read_website, memory.recall],
    system_message=SystemMessage(
        "You are webgpt. You research by using google search, reading websites, and recalling memories of websites you read. Once you gathered enough information, you end the conversation by answering the question. You cite sources in the answer text as [1], [2] etc."
    ),
    prompt_template="{query}".format,
    # on_assistant_message=lambda message: print(message),
    # on_user_message=lambda message: print(message),
    on_function_message=lambda message: print(message),
    response_openapi=AnswerWithCitations,
)
