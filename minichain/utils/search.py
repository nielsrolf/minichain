import os
from pprint import PrettyPrinter

import click
from dotenv import load_dotenv
from serpapi import GoogleSearch
from duckduckgo_search import DDGS

from minichain.utils.disk_cache import disk_cache
from dataclasses import dataclass

pprint = PrettyPrinter(indent=4).pprint


load_dotenv()

@dataclass
class SearchResult:
    title: str
    snippet: str
    link: str

def google_search(query: str) -> list[SearchResult]:
    search = GoogleSearch({"q": query, "api_key": os.getenv("SERP_API_KEY")})
    keys = [
        "title",
        "snippet",
        "link",
    ]
    results = search.get_dict()["organic_results"]
    result = [{k: i.get(k) for k in keys if i.get(k)} for i in results]
    result = [SearchResult(title=i['title'], snippet=i['snippet'], link=i['link']) for i in result]
    return result



def duckduckgo_search(query: str) -> list[SearchResult]:
    results = []
    with DDGS() as ddgs:
        for res in  ddgs.text(query, timelimit="y"):
            results.append(SearchResult(title=res["title"], snippet=res["body"], link=res["href"]))
    return results

@click.command()
@click.argument("query")
def main(query):
    print("GOOGLE RESULT")
    pprint(google_search(query))
    print("DUCKDUCKGO RESULT")
    pprint(duckduckgo_search(query))




if __name__ == "__main__":
    main()
