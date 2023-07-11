from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from minichain.agent import (Agent, AssistantMessage, Function, FunctionCall,
                             FunctionMessage, SystemMessage, UserMessage)
from minichain.tools.recursive_summarizer import long_document_qa
from minichain.tools.text_to_memory import (Memory, MemoryWithMeta,
                                            text_to_memory)
from minichain.utils.markdown_browser import markdown_browser


class KeywordList(BaseModel):
    keywords: List[str] = Field(..., description="A list of keywords.")


snippet_template = """## {title}
Context: {context}
Source: {source}
Content: {content}
"""


class VectorDB:
    def __init__(self):
        pass

    def encode(self, questions):
        pass

    def search(self, query_embeddings, num_results=3):
        pass

    def add(self, key, value):
        key_embedding = self.encode([key])
        # self.index.add(key_embedding, value)


class IngestQuery(BaseModel):
    url: str = Field(..., description="The url of the website to read and tag.")


class RecallQuery(BaseModel):
    question: str = Field(..., description="The question to search for.")



class SemanticParagraphMemory:
    def __init__(self):
        self.memories: List[MemoryWithMeta] = []
        self.vector_db = None
        self.snippet_template = snippet_template
        self.read_website = Function(
            name="read_website",
            openapi=IngestQuery,
            function=self._read_website,
            description="Read a website and create annoted memories.",
        )
        self.recall = Function(
            name="recall",
            openapi=RecallQuery,
            function=self._recall,
            description="Recall memories based on a question.",
        )

    def ingest(self, content, source):
        memories = text_to_memory(content, source)
        self.memories += memories
        return self.get_available_tags(memories)

    def search_by_vector(self, question, num_results=8):
        query_questions = self.generate_questions(question)
        query_embeddings = self.vector_db.encode(query_questions)
        matches = self.vector_db.search(query_embeddings, num_results=num_results * 2)
        # Get the highest score for each memory-id (memories can occur multiple times)
        scores = {}
        for i in matches:
            if i.id not in scores or i.score > scores[i.id]:
                scores[i.id] = i.score
        # Sort by score
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        # Get the top results
        top_results = sorted_scores[:num_results]
        # Get the memories
        memory_ids = [i[0] for i in top_results]
        results = [i for i in self.memories if i.id in memory_ids]
        return results

    def search_by_keywords(self, question, num_results=8):
        keywords = self.generate_keywords(question)
        scores = [len(set(keywords) & set(i.memory.tags)) for i in self.memories]
        highest_scoring_memories = sorted(zip(scores, self.memories), reverse=True, key=lambda i: i[0])[
            :num_results
        ]
        results = [i[1] for i in highest_scoring_memories]
        return results

    def get_available_tags(self, memories=None):
        if memories is None:
            memories = self.memories
        return list(set([i for i in memories for i in i.memory.tags]))
    
    def generate_keywords(self, question):
        # Use gpt to generate keywords
        available_tags = self.get_available_tags()
        keyword_agent = Agent(
            # system_message=SystemMessage(
            #     f"You are a memory retrieval assistant. You have memories with the following tags: {available_tags}. Your task is to list all tags from the list that might be associated with information relevant to the question provided by the user. Do not respond with tags that are not in the list. Respond with the most relevant tags first. When in doubt, respond with more tags rather than less."
            # ),
            system_message=SystemMessage(
                f"You are a memory retrieval assistant. You select tags of memories related to the question: '{question}'. When the user sends a list of tags, reply with a subset of those keywords that are most relevant to the question. When in doubt, respond with more tags rather than less. Respond with a json structure with one 'keywords' fields."
            ),
            prompt_template="{available_tags}".format,
            functions=[],
            response_openapi=KeywordList,
        )
        keywords = keyword_agent.run(available_tags=available_tags)["keywords"]
        print("looking for keywords", keywords)
        return keywords

    def semantic_search(self, question):
        keyword_results = self.search_by_keywords(question)
        print(keyword_results)
        vector_results = []
        # vector_results = self.search_by_vector(question)
        results = keyword_results + vector_results
        # filter duplicates by id
        results = [
            i
            for n, i in enumerate(results)
            if i.id not in [x.id for x in results[n + 1 :]]
        ]
        result = self.rank_or_summarize(results, question)
        return result

    def rank_or_summarize(self, results, question):
        if len(results) == 0:
            return "No relevant memories found."
        elif len(results) == 1:
            return results[0]
        else:
            return self.summarize(results, question)

    def summarize(self, results, question):
        snippets = [self.format_as_snippet(memory) for memory in results]
        document = "\n\n".join(snippets)
        print("-" * 80)
        print("-" * 80)
        print(document)
        summary = long_document_qa(text=document, question=question)
        return summary

    def format_as_snippet(self, memory):
        return self.snippet_template.format(
            source=memory.meta.source,
            title=memory.memory.title,
            context=memory.memory.context,
            content=memory.meta.content,
        )
    
    def _read_website(self, query: IngestQuery):
        text = markdown_browser(query.url)
        available_tags = self.ingest(text, query.url)
        return f"You now have new memories with the following tags: {available_tags}"
    
    def _recall(self, query: RecallQuery):
        results = self.semantic_search(query.question)
        return results


def test_semantic_paragraph_memory():
    from minichain.utils.markdown_browser import markdown_browser

    memory = SemanticParagraphMemory()
    url = "https://en.wikipedia.org/wiki/Python_(programming_language)"
    text = markdown_browser(url)
    memory.ingest(text, url)
    result = memory.semantic_search("What is the latest version of Python?")
    print(result)
    breakpoint()


if __name__ == "__main__":
    test_semantic_paragraph_memory()
