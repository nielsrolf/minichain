from dataclasses import dataclass
from duckduckgo_search import DDGS
from pprint import pprint


@dataclass
class AnswerResult:
    topic: str
    text: str
    url: str

def duckduckgo_answer(query: str) -> list[AnswerResult]:
    results = []
    with DDGS() as ddgs:
        for res in  ddgs.answers(query):
            results.append(AnswerResult(topic=res["topic"], text=res["text"], url=res["url"]))
    return results


if __name__ == "__main__":
    results = duckduckgo_answer("gravity")
    pprint(results)