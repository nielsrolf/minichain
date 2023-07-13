from pydantic import BaseModel, Field

from minichain.agent import (Agent, AssistantMessage, Function, FunctionCall,
                             FunctionMessage, SystemMessage, UserMessage)
from minichain.memory import SemanticParagraphMemory
from minichain.tools.recursive_summarizer import long_document_qa
from minichain.utils.markdown_browser import markdown_browser
from minichain.utils.search import google_search


class SearchQuery(BaseModel):
    query: str = Field(..., description="The query to search for.")


google_search_function = Function(
    name="google_search",
    openapi=SearchQuery,
    function=google_search,
    description="Use google to search the web for a query.",
)
