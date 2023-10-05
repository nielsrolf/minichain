import json
import math
import os
import pickle
import re
from dataclasses import dataclass
from typing import Any, List, Optional
import uuid
import hashlib

import numpy as np
from pydantic import BaseModel, Field

from minichain.agent import Agent
from minichain.functions import Function, tool
from minichain.tools.codebase import default_ignore_files, get_visible_files
from minichain.tools.recursive_summarizer import long_document_qa, text_scan
from minichain.tools.text_to_memory import MemoryWithMeta, text_to_memory, add_line_numbers
from minichain.utils.cached_openai import get_embedding
from minichain.utils.json_datetime import datetime_parser, datetime_converter


snippet_template = """## {title}
Context: {context}
Source: {source}:{start_line}-{end_line}
```
{content}
```
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
        description="A list of all question that should be answered in order to answer the original question. Should be 1-4 questions.",
    )


def hash_string(string):
        return hashlib.sha256(string.encode("utf-8")).hexdigest()

class SemanticParagraphMemory:
    def __init__(
        self,
        use_vector_search=False,
        use_content_scan_search=False,
        auto_save_dir=".minichain/memory",
        agents_kwargs={},
    ):
        assert use_vector_search or use_content_scan_search, (
            "At least one of the search methods must be enabled. "
            "Set use_vector_search or use_content_scan_search to True."
        )
        self.use_vector_search = use_vector_search
        self.use_content_scan_search = use_content_scan_search
        self.num_search_methods = int(use_vector_search) + int(use_content_scan_search)
        self.memories: List[MemoryWithMeta] = []
        self.vector_db = VectorDB()
        self.snippet_template = snippet_template
        self.recall = Function(
            name="recall",
            openapi=RecallQuery,
            function=self._recall,
            description="Recall memories based on a question.",
        )
        self.auto_save_dir = auto_save_dir
        self.agent_kwargs = agents_kwargs
        self.ingested_hashed = {}

    def register_stream(self, stream):
        self.agent_kwargs["stream"] = stream
    
    def check_if_still_valid(self, memory, content=None):
        # Checks if the remembered raw text still appears in the source file and potentially 
        # updates the lines
        if not memory.meta.watch_source:
            return True
        if content is None:
            try:
                with open(memory.meta.source, "r") as f:
                    content = f.read()
            except FileNotFoundError:
                content = ""
        if memory.meta.content not in content:
            try:
                self.memories.remove(memory)
            except ValueError:
                pass
            return False
                
        placeholder = uuid.uuid4().hex
        content = content.replace(memory.meta.content, placeholder)
        lines = content.split("\n")
        if lines[memory.memory.start_line - 1] == placeholder:
            return True
        
        start_line = lines.index(placeholder) + 1
        end_line = start_line + len(memory.meta.content.split("\n")) - 1
        memory.memory.start_line = start_line
        memory.memory.end_line = end_line
        return True

    async def ingest(self, content, source, watch_source=True):
        """Ingest a text and create memories from it.
        
        If memories for this source exist already, this method updates the memories by:
        - returning if the content has not changed since last ingestion
        - updating line ranges of existing memories
        - deleting memories that are not valid anymore
        - adding new memories on the diff since the last ingestion
        """
        content_hash = hash_string(content)
        existing_memories = [i for i in self.memories if i.meta.source == source]
        if self.ingested_hashed.get(source) == content_hash:
            return existing_memories
        existing_memories = [i for i in existing_memories if self.check_if_still_valid(i, content)]
        memories = await text_to_memory(text=content, source=source, agent_kwargs=self.agent_kwargs, existing_memories=existing_memories)
        # Add memories to vector db
        for memory in memories:
            memory.meta.watch_source = watch_source
            # title
            self.vector_db.add(memory.memory.title, memory)
            # questions
            for question in memory.memory.relevant_questions:
                key = f"({memory.meta.source}): {question}"
                self.vector_db.add(key, memory)
        self.memories += memories
        self.ingested_hashed[source] = content_hash
        if self.auto_save_dir is not None:
            self.save(self.auto_save_dir)
        return memories

    async def search_by_vector(self, question, num_results) -> List[MemoryWithMeta]:
        # query_questions = await self.generate_questions(question)
        query_questions = [question]
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

    async def generate_questions(self, question: str) -> List[str]:
        # Use gpt to generate questions
        if question.strip() == "":
            return [""]
        question_agent = Agent(
            system_message=f"The user provides you with a question. Generate a list of sub-questions that are relevant to the question. These questions are used to retrieve memories, which are then used to answer the question.",
            prompt_template="{question}".format,
            functions=[],
            response_openapi=RelatedQuestionList,
            **self.agent_kwargs,
        )
        questions = await question_agent.run(question=question)
        questions = questions["sub_questions"]
        print("Question: ", question)
        print("Sub-questions: ", questions)
        if question not in questions:
            questions = [question] + questions
        return questions

    async def retrieve(self, question: str, num_results=8) -> List[MemoryWithMeta]:
        results = []
        num_results_per_search = math.ceil(num_results / self.num_search_methods)
        if self.use_vector_search:
            results += await self.search_by_vector(question, num_results_per_search)
        if self.use_content_scan_search:
            results += await self.search_by_content_scan(
                question, num_results_per_search
            )
        # filter duplicates by id
        results = [
            i
            for n, i in enumerate(results)
            if i.id not in [x.id for x in results[n + 1 :]]
        ]
        update_needed = False
        for i in results:
            if not self.check_if_still_valid(i):
                update_needed = True
                await self.ingest_rec(i.meta.source)
        if update_needed:
            results = await self.retrieve(question, num_results)
        return results

    async def answer_from_memory(self, question: str):
        results = await self.retrieve(question)
        result = await self.rank_or_summarize(results, question)
        return result

    async def rank_or_summarize(self, results, question) -> str:
        # TODO
        if len(results) == 0:
            return "No relevant memories found."
        else:
            return await self.summarize(results, question)

    async def summarize(self, results, question) -> str:
        snippets = [
            self.format_as_snippet(memory)
            for memory in results
            if memory.memory.type == "content"
        ]
        document = f"Here are the memories that I found that might be relevant to the question: {question}"
        document += "\n\n".join(snippets)
        document += f"\nIf these memories are insufficient to answer the question, they may contain some information that will help decide where to look for the answer (such as `I couldn't find the relevant info but it seems like the answer could be in this file: ...`)"
        print("-" * 80)
        print("-" * 80)
        print(document)
        # TODO
        summary = await long_document_qa(
            text=document,
            question=question,
        )
        return summary

    def format_as_snippet(self, memory) -> str:
        return self.snippet_template.format(
            source=memory.meta.source,
            title=memory.memory.title,
            context=memory.memory.context,
            content=memory.meta.content,
            start_line=memory.memory.start_line,
            end_line=memory.memory.end_line,
        )

    async def _recall(self, query: RecallQuery):
        results = await self.answer_from_memory(query.question)
        return results

    def print(self):
        print(self.get_content_summary())

    def get_content_summary(self, memories=None):
        memories = memories or self.memories
        summary = ""
        # group by source
        memories_by_source = {}
        for memory in memories:
            memories_by_source[memory.meta.source] = memories_by_source.get(
                memory.meta.source, []
            ) + [memory]
        if len(memories) > 15:
            if len(memories_by_source.keys()) > 15:
                summary += f"You have {len(memories)} memories from {len(memories_by_source.keys())} sources.\n"
                return summary
            summary += f"You have {len(memories)} memories from the following sources:\n"
            for source, memories_of_source in memories_by_source.items():
                summary += f"- {source}: {len(memories_of_source)}\n"
            return summary
        else:
            for source, memories in memories_by_source.items():
                summary += f"# Memories from: {source} \n"
                for i in memories:
                    summary += i.memory.title + "\n"
            return summary

    def get_queue_summary(self, queue):
        queue = sorted(queue, reverse=True, key=lambda i: i.priority)
        summary = ""
        for item in queue:
            question_list = "\n  ".join(item.expected_answers)
            summary += f"{item.url}: {question_list}  \n"
        return summary

    async def search_by_content_scan(
        self, question, num_results
    ) -> List[MemoryWithMeta]:
        content_summary = self.get_content_summary()
        # Use long document qa to generate a list of titles to search for
        titles = await text_scan(
            text=content_summary,
            response_openapi=TitleScore,
            system_message=f"List all titles related to the question: {question}.",
            **self.agent_kwargs,
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
            # we need to handle the datetime objects and save them as e.g. 2023-12-31T23:59:59.999999+00:00
            json.dump([i.dict() for i in self.memories], f, default=datetime_converter)
        with open(os.path.join(memory_dir, "ingested_hashed.json"), "w") as f:
            json.dump(self.ingested_hashed, f)

    def load(self, memory_dir):
        # load the vector db
        with open(os.path.join(memory_dir, "vector_db_keys.pkl"), "rb") as f:
            self.vector_db.keys = pickle.load(f)
        with open(os.path.join(memory_dir, "vector_db_values.pkl"), "rb") as f:
            self.vector_db.values = pickle.load(f)
        with open(os.path.join(memory_dir, "memories.json"), "r") as f:
            memories = json.load(f, object_hook=datetime_parser)
        try:
            with open(os.path.join(memory_dir, "ingested_hashed.json"), "r") as f:
                ingested_hashed = json.load(f)
                for key, hash in ingested_hashed.items():
                    if any([i.meta.source == key for i in self.memories]):
                        self.ingested_hashed[key] = hash
        except:
            pass
        self.memories = [MemoryWithMeta(**i) for i in memories]

    def find_memory_tool(self):
        @tool()
        async def find_memory(
            question: str = Field(..., description="The question to search for."),
            num_results: int = Field(
                5,
                description="The number of raw memories to return or consider before answering. The results are ranked by relevance.",
            ),
            output: str = Field(
                "answer",
                description="The output format. Allowed values are: ['answer', 'raw']. Select 'raw' in order to retrieve the content of the original memory, e.g. in order to retrieve code.",
            )
        ):
            """Search memories related to a question."""
            results = await self.retrieve(question, num_results=num_results)
            if output == "answer":
                result = await self.rank_or_summarize(results, question)
            elif output == "raw":
                result = "\n\n".join([self.format_as_snippet(i) for i in results])
            return result

        def register_stream(stream):
            self.register_stream(stream)
            find_memory.stream = stream

        find_memory.register_stream = register_stream

        return find_memory
    
    async def ingest_rec(self, path):
        print("Ingesting: ", path)
        new_memories = []
        if os.path.isdir(path):
            files = get_visible_files(path)
            for file in files:
                filepath = os.path.join(path, file)
                new_memories += await self.ingest_rec(filepath)
        else:
            with open(path, "r") as f:
                content = f.read()
            new_memories += await self.ingest(content, path)
        return new_memories

    def ingest_tool(self):
        @tool()
        async def create_memories_from_file(
            path: str = Field(
                ...,
                description="The path to the dir or file to ingest. If a dir is provided, all files in the dir are ingested. If memories already exist, they are updated.",
            )
        ):
            """Read a file and create memories from it."""
            new_memories = await self.ingest_rec(path)
            summary = self.get_content_summary(new_memories)
            return f"Ingested {path}. New memories formed:\n{summary} "

        def register_stream(stream):
            self.register_stream(stream)
            create_memories_from_file.stream = stream

        create_memories_from_file.register_stream = register_stream

        return create_memories_from_file


async def main():
    memory = SemanticParagraphMemory(use_vector_search=True)
    test_file = "minichain/utils/docker_sandbox.py"
    with open(test_file, "r") as f:
        content = f.read()
    await memory.ingest(content, test_file)
    memory.save("test_memory")
    print(memory.get_content_summary())
    print("======================================")
    question = "with which command is the docker container started?"

    async def print_qa(question):
        print(question)
        answer = await memory.answer_from_memory(question)
        breakpoint()
        print(answer)

    await print_qa(question)

    print("======================================")
    try:
        question = input("Ask a question: ")
        while question != "exit":
            answer = await memory.answer_from_memory(question)
            print(answer)
            question = input("Ask a question: ")
    except:
        breakpoint()
    print("Bye")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
