from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union

from minichain.agent import (Agent, AssistantMessage, Function, FunctionCall,
                             FunctionMessage, SystemMessage, UserMessage)


@dataclass
class Paragraph:
    content: str
    source: str
    summary: str
    relevant_questions: List[str]


class SemanticParagraphMemory:
    def __init__(self):
        self.paragraphs = []
        self.vector_db = None

    def ingest(self, content, source):
        for paragraph in self.split(content, source):
            self.paragraphs.append(paragraph)

    def split(self, content, source):
        """Use an agent that splits the paragraphs by line numbers into semantic paragraphs
        - split into 3k token chunks with 200 token overlap
        - use an agent with functions to add the next paragraph to the memory
        - assert that each line is covered at least once, otherwise return error
        - continue until done
        """

    def search_by_vector(self, question):
        pass

    def search_by_keywords(self, question):
        keywords = self.generate_keywords(question)
        results = [i for i in self.paragraphs if keywords.intersection(i.keywords)]
        return results

    def generate_keywords(self, question):
        # Use gpt to generate keywords
        keyword_agent = Agent(
            "Generate search query keywords for the question provided by the user. These keywords will be matched against a memory of paragraphs that are annoted with keywords. Answer by return a comma separated list of keywords.",
            prompt_template="{question}",
            functions=[],
        )
        keywords = keyword_agent.run(question)
        return keywords

    def semantic_search(self, question):
        keyword_results = self.search_by_keywords(question)
        vector_results = self.search_by_vector(question)
        results = keyword_results + vector_results
        result = self.rank_or_summarize(results)
        return result

    def rank_or_summarize(self, results):
        pass
