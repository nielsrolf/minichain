from pydantic import Field

from minichain.functions import tool
from minichain.utils.search import google_search


@tool(name="google_search")
async def web_search(query: str = Field(..., description="The query to search for.")):
    """Use google to search the web for a query."""
    results = google_search(query)
    return results
