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
    function=lambda search_query: google_search(search_query.query),
    description="Use google to search the web for a query.",
)


def test_google_search():
    agent = Agent(
        functions=[google_search_function, long_document_qa],
        system_message=SystemMessage("Use google to search the web for a query."),
        prompt_template="{query}".format,
        onAssistantMessage=lambda message: print(message),
        onUserMessage=lambda message: print(message),
        onFunctionMessage=lambda message: print(message),
    )
    query = "What is the capital of France?"
    result = agent.run(query=query)
    print(result)
    assert result.content == "Paris"


if __name__ == "__main__":
    test_google_search()
