import json
import math
import os
import pickle
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union

import numpy as np
from pydantic import BaseModel, Field

from minichain.agent import (Agent, AssistantMessage, Function, FunctionCall,
                             FunctionMessage, SystemMessage, UserMessage)
from minichain.tools.recursive_summarizer import long_document_qa, text_scan
from minichain.tools.text_to_memory import (Memory, MemoryWithMeta,
                                            text_to_memory)
from minichain.utils.cached_openai import get_embedding
from minichain.utils.markdown_browser import markdown_browser


class KeywordList(BaseModel):
    keywords: List[str] = Field(..., description="A list of keywords.")


snippet_template = """## {title}
Context: {context}
Source: {source}
Content: {content}
"""


@dataclass
class VectorSearchScore:
    score: float
    value: Any


class TitleScore(BaseModel):
    title: str = Field(
        ..., description="Title of the document as written in the input text."
    )
    score: int = Field(
        ...,
        description="The score of how relevant this document seems to be. A score of 80 means there is an 80% chance that this document contains the answer to the question.",
    )


class VectorDB:
    def __init__(self, embedding_function=get_embedding):
        self.values = []
        self.keys = []
        self.embedding_function = embedding_function

    def encode(self, texts):
        return np.array([self.embedding_function(text) for text in texts])

    def search(self, query_embeddings, num_results=3) -> List[VectorSearchScore]:
        scores = np.dot(query_embeddings, np.array(self.keys).T)
        selection = []
        num_results = max(num_results // len(query_embeddings), 1)
        for i in range(len(scores)):
            indices = np.argsort(scores[i])[::-1][:num_results]
            selection += [
                VectorSearchScore(scores[i][j], self.values[j]) for j in indices
            ]
        # remove duplicates
        selection = sorted(selection, key=lambda x: x.score, reverse=True)
        deduplicated = []
        deduplicated_keys = []
        for i in selection:
            if i.value.id not in deduplicated_keys:
                deduplicated.append(i)
                deduplicated_keys.append(i.value.id)
        return deduplicated

    def add(self, key, value):
        key_embedding = self.encode([key])[0]
        self.keys.append(key_embedding)
        self.values.append(value)


class IngestQuery(BaseModel):
    url: str = Field(..., description="The url of the website to read and tag.")
    question: Optional[str] = Field(
        None, description="The question you are trying to answer."
    )


class RecallQuery(BaseModel):
    question: str = Field(..., description="The question to search for.")


class RelatedQuestionList(BaseModel):
    sub_questions: List[str] = Field(
        ...,
        description="A list of all question that should be answered in order to answer the original question.",
    )


class SemanticParagraphMemory:
    def __init__(
        self,
        use_vector_search=True,
        use_keywords_search=False,
        use_content_scan_search=True,
    ):
        self.use_vector_search = use_vector_search
        self.use_keywords_search = use_keywords_search
        self.use_content_scan_search = use_content_scan_search
        self.num_search_methods = (
            int(use_vector_search)
            + int(use_keywords_search)
            + int(use_content_scan_search)
        )
        self.memories: List[MemoryWithMeta] = []
        self.vector_db = VectorDB()
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
        # Add memories to vector db
        for memory in memories:
            # title
            self.vector_db.add(memory.memory.title, memory)
            # questions
            for question in memory.memory.relevant_questions:
                self.vector_db.add(question, memory)
        self.memories += memories
        return memories

    def search_by_vector(self, question, num_results) -> List[MemoryWithMeta]:
        query_questions = self.generate_questions(question)
        query_embeddings = self.vector_db.encode(query_questions)
        matches = self.vector_db.search(query_embeddings, num_results=num_results * 2)
        # Get the highest score for each memory-id (memories can occur multiple times)
        scores = {
            i.value.id: max([j.score for j in matches if j.value.id == i.value.id])
            for i in matches
        }
        # Sort by score
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        # Get the top results
        top_results = sorted_scores[:num_results]
        # Get the memories
        memory_ids = [i[0] for i in top_results]
        results = [i for i in self.memories if i.id in memory_ids]
        return results[:num_results]

    def search_by_keywords(self, question, num_results) -> List[MemoryWithMeta]:
        keywords = self.generate_keywords(question)
        scores = [len(set(keywords) & set(i.memory.tags)) for i in self.memories]
        highest_scoring_memories = sorted(
            zip(scores, self.memories), reverse=True, key=lambda i: i[0]
        )[:num_results]
        results = [i[1] for i in highest_scoring_memories]
        return results

    def get_available_tags(self, memories=None) -> List[str]:
        if memories is None:
            memories = self.memories
        return list(set([i for i in memories for i in i.memory.tags]))

    def generate_keywords(self, question) -> List[str]:
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

    def generate_questions(self, question: str) -> List[str]:
        # Use gpt to generate questions
        question_agent = Agent(
            system_message=SystemMessage(
                f"The user provides you with a question. Generate a list of sub-questions that are relevant to the question. These questions are used to retrieve memories, which are then used to answer the question."
            ),
            prompt_template="{question}".format,
            functions=[],
            response_openapi=RelatedQuestionList,
        )
        questions = question_agent.run(question=question)["sub_questions"]
        print("Question: ", question)
        print("Sub-questions: ", questions)
        if question not in questions:
            questions = [question] + questions
        return questions

    def retrieve(self, question: str, num_results=8) -> List[MemoryWithMeta]:
        results = []
        num_results_per_search = math.ceil(num_results / self.num_search_methods)
        if self.use_keywords_search:
            results += self.search_by_keywords(question, num_results_per_search)
        if self.use_vector_search:
            results += self.search_by_vector(question, num_results_per_search)
        if self.use_content_scan_search:
            results += self.search_by_content_scan(question, num_results_per_search)
        # filter duplicates by id
        results = [
            i
            for n, i in enumerate(results)
            if i.id not in [x.id for x in results[n + 1 :]]
        ]
        return results

    def answer_from_memory(self, question: str):
        results = self.retrieve(question)
        result = self.rank_or_summarize(results, question)
        return result

    def rank_or_summarize(self, results, question) -> str:
        if len(results) == 0:
            return "No relevant memories found."
        elif len(results) == 1:
            return results[0]
        else:
            return self.summarize(results, question)

    def summarize(self, results, question) -> str:
        snippets = [
            self.format_as_snippet(memory)
            for memory in results
            if memory.memory.type == "content"
        ]
        document = "\n\n".join(snippets)
        print("-" * 80)
        print("-" * 80)
        print(document)
        summary = long_document_qa(text=document, question=question)
        return summary

    def format_as_snippet(self, memory) -> str:
        return self.snippet_template.format(
            source=memory.meta.source,
            title=memory.memory.title,
            context=memory.memory.context,
            content=memory.meta.content,
        )

    def _read_website(self, url: str, question: str = None):
        text = markdown_browser(url)
        new_memories = self.ingest(text, url)
        queue = []
        for memory in new_memories:
            queue += memory.memory.links

        content_summary = ""

        if len(new_memories) > 0:
            content_summary += f"New memories were created from the website {url}:\n"
            content_summary += self.get_content_summary(new_memories)

        if len(queue) > 0:
            content_summary += f"You encountered the following links that you can read next if needed:\n"
            content_summary += self.get_queue_summary(queue)

        if question is not None:
            current_answer = self.answer_from_memory(question)
            content_summary += f"A current answer to the question '{question}', based on the memories you have is: \n"
            content_summary += f"{current_answer}\n\n"
            content_summary += "If this is a satisfactory answer, you can stop and respond to the user. If not, continue browsing."

        return content_summary

    def _recall(self, query: RecallQuery):
        results = self.answer_from_memory(query.question)
        return results

    def print(self):
        print(self.get_content_summary())

    def get_content_summary(self, memories=None):
        memories = memories or self.memories
        summary = "======= MEMORY CONTENT =======\n"
        # group by source
        memories_by_source = {}
        for memory in memories:
            memories_by_source[memory.meta.source] = memories_by_source.get(
                memory.meta.source, []
            ) + [memory]
        for source, memories in memories_by_source.items():
            summary += f"# Memories from: {source} \n"
            for i in memories:
                summary += i.memory.title + "\n"
                summary += f"    {i.memory.tags}\n"
        return summary

    def get_queue_summary(self, queue):
        queue = sorted(queue, reverse=True, key=lambda i: i.priority)
        summary = "======= ENCOUNTERED LINKS =======\n"
        for item in queue:
            question_list = "\n  ".join(item.expected_answers)
            summary += f"{item.url}: {question_list}  \n"
        return summary

    def search_by_content_scan(self, question, num_results) -> List[MemoryWithMeta]:
        content_summary = self.get_content_summary()
        # Use long document qa to generate a list of titles to search for
        titles = text_scan(
            text=content_summary,
            response_openapi=TitleScore,
            system_message=f"List all titles related to the question: {question}.",
        )
        titles = sorted(titles, reverse=True, key=lambda i: i["score"])[:num_results]
        titles = [i["title"] for i in titles]
        print("Titles: ", titles)
        selection = []
        # Search for each title
        for title in titles:
            selection.append(self.search_by_title(title))
        return selection

    def search_by_title(self, title: str) -> MemoryWithMeta:
        # Remove enumeration if it exists
        title = re.sub(r"^\d+\.\s+", "", title)
        # Check for exact title match
        for memory in self.memories:
            if memory.memory.title.lower() == title.lower():
                return memory
        query_embeddings = self.vector_db.encode([title])
        match = self.vector_db.search(query_embeddings, 1)[0]
        return match.value

    def save(self, memory_dir):
        os.makedirs(memory_dir, exist_ok=True)
        # save the vector db
        with open(os.path.join(memory_dir, "vector_db_keys.pkl"), "wb") as f:
            pickle.dump(self.vector_db.keys, f)
        with open(os.path.join(memory_dir, "vector_db_values.pkl"), "wb") as f:
            pickle.dump(self.vector_db.values, f)
        # save the memories as json
        with open(os.path.join(memory_dir, "memories.json"), "w") as f:
            json.dump([i.dict() for i in self.memories], f)

    def load(self, memory_dir):
        # load the vector db
        with open(os.path.join(memory_dir, "vector_db_keys.pkl"), "rb") as f:
            self.vector_db.keys = pickle.load(f)
        with open(os.path.join(memory_dir, "vector_db_values.pkl"), "rb") as f:
            self.vector_db.values = pickle.load(f)
        with open(os.path.join(memory_dir, "memories.json"), "r") as f:
            memories = json.load(f)
        self.memories = [MemoryWithMeta(**i) for i in memories]


if __name__ == "__main__":
    url = "https://en.wikipedia.org/wiki/Python_(programming_language)"
    memory = SemanticParagraphMemory(
        use_content_scan_search=input("Use content scan search? (y/n) ") == "y",
        use_keywords_search=input("Use keywords search? (y/n) ") == "y",
        use_vector_search=input("Use vector search? (y/n) ") == "y",
    )
    text = markdown_browser(url)
    memory.ingest(text, url)
    memory.print()
    try:
        while question := input("Question: "):
            print(memory.answer_from_memory(question))
    except KeyboardInterrupt:
        from pprint import pprint

        retrieved = memory.retrieve(question)
        for i in retrieved:
            pprint(i.dict())
        breakpoint()
