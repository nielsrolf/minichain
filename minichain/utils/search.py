import os
from pprint import PrettyPrinter

import click
from dotenv import load_dotenv
from serpapi import GoogleSearch

from minichain.utils.disk_cache import disk_cache

pprint = PrettyPrinter(indent=4).pprint


load_dotenv()


# @disk_cache  # remove at production
def google_search(query):
    search = GoogleSearch({"q": query, "api_key": os.getenv("SERP_API_KEY")})
    keys = [
        "title",
        "snippet",
        "link",
    ]
    results = search.get_dict()["organic_results"]
    result = [{k: i.get(k) for k in keys if i.get(k)} for i in results]
    return result


@click.command()
@click.argument("query")
def main(query):
    pprint(google_search(query))


if __name__ == "__main__":
    main()
