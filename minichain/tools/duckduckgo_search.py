from pydantic import BaseModel, Field

from minichain.agent import (
    Function,
)
from minichain.utils.search import duckduckgo_search, google_search


class SearchQuery(BaseModel):
    query: str = Field(..., description="The query to search for.")


duckduckgo_search_function = Function(
    name="google_search",
    openapi=SearchQuery,
    function=duckduckgo_search,
    description="Use google to search the web for a query.",
)
