import json
import os
import pickle
from dataclasses import dataclass
from typing import Any, List, Optional
import uuid
import hashlib

import numpy as np
from pydantic import BaseModel, Field

from minichain.functions import tool
from minichain.tools.codebase import get_visible_files, open_or_search_file
from minichain.tools.text_to_memory import MemoryWithMeta, text_to_memory, text_to_single_memory
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


class VectorDB:
    def __init__(self, embedding_function=get_embedding):
        self.values = {}
        self.keys = {}
        self.embedding_function = embedding_function

    def encode(self, texts):
        return np.array([self.embedding_function(text) for text in texts])
    
    def _dict_to_list(self, dict):
        return [dict[key] for key in sorted(self.keys.keys())]

    def search(self, query_questions, num_results=3) -> List[VectorSearchScore]:
        query_embeddings = self.encode(query_questions)
        K, V = self._dict_to_list(self.keys), self._dict_to_list(self.values)
        scores = np.dot(query_embeddings, np.array(K).T)
        selection = []
        num_results = max(num_results // len(query_embeddings), 1)
        for i in range(len(scores)):
            indices = np.argsort(scores[i])[::-1][:num_results]
            selection += [
                VectorSearchScore(scores[i][j], V[j]) for j in indices
            ]
            # print what contributes to the score
            for j in indices:
                print(f"{query_questions[i]} -> {V[j].memory.title} ({scores[i][j]})")
        # remove duplicates
        deduplicated = []
        deduplicated_keys = []
        for i in selection:
            if i.value.id not in deduplicated_keys:
                deduplicated.append(i)
                deduplicated_keys.append(i.value.id)
        return deduplicated

    def add(self, key, value):
        key_embedding = self.encode([key])[0]
        key_hash = hash_string(key)
        self.keys[key_hash] = key_embedding
        self.values[key_hash] = value
    
    def remove_key(self, key):
        key_hash = hash_string(key)
        del self.keys[key_hash]
        del self.values[key_hash]
    
    def remove_value(self, value):
        delete = []
        for k, v in self.values.items():
            if v.id == value.id:
                delete += [k]
        for k in delete:
            del self.keys[k]
            del self.values[k]
    

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
        auto_save_dir=".minichain/memory",
        agents_kwargs={},
    ):
        self.memories: List[MemoryWithMeta] = []
        self.vector_db = VectorDB()
        self.snippet_template = snippet_template
        self.auto_save_dir = auto_save_dir
        self.agent_kwargs = agents_kwargs
        self.ingested_hashed = {}

    def register_message_handler(self, message_handler):
        self.agent_kwargs["message_handler"] = message_handler

    # Ingestion
    def forget(self, memory):
        try:
            self.vector_db.remove_value(memory)
            self.memories.remove(memory)
        except ValueError:
            pass
    
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
                self.forget(memory)
            except ValueError:
                pass
            return False
                
        placeholder = uuid.uuid4().hex
        content = content.replace(memory.meta.content, "\n" + placeholder + "\n")
        lines = content.split("\n")
        try:
            if lines[max(0, memory.memory.start_line - 1)] == placeholder:
                return True
        except IndexError:
            # file is potentially shorter than before
            pass
        start_line = lines.index(placeholder)
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

    async def ingest_rec(self, path):
        if not os.path.exists(path):
            return []
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
    
    async def add_single_memory(self, source, content, scope, watch_source=False):
        memory = await text_to_single_memory(content, source)
        memory.meta.scope = scope
        memory.meta.watch_source = watch_source
        self.memories.append(memory)
        self.vector_db.add(memory.memory.title, memory)
        for question in memory.memory.relevant_questions:
            key = f"({memory.meta.source}): {question}"
            self.vector_db.add(key, memory)
        if self.auto_save_dir is not None:
            self.save(self.auto_save_dir)
        return memory
    
    async def search_by_vector(self, question, num_results) -> List[MemoryWithMeta]:
        # query_questions = await self.generate_questions(question)
        query_questions = [question]
        matches = self.vector_db.search(query_questions, num_results=num_results * 2)
        # remove all matches that are out of scope
        matches = [i for i in matches if i.value.memory.type == "content"]
        # remove all matches that are out of scope
        matches_in_scope, scope = [], ["root"]
        if self.agent_kwargs.get("message_handler"):
            scope = self.agent_kwargs["message_handler"].path
        for match in matches:
            if match.value.meta.scope in scope:
                matches_in_scope.append(match)
        return [i.value for i in matches_in_scope[:num_results]]

    async def retrieve(self, question: str, num_results=8) -> List[MemoryWithMeta]:
        results = await self.search_by_vector(question, num_results)
        sources_to_update = []
        for i in results:
            if not self.check_if_still_valid(i):
                sources_to_update.append(i.meta.source)
        if len(sources_to_update) > 0:
            for source in list(set(sources_to_update)):
                await self.ingest_rec(source)
            results = await self.retrieve(question, num_results)
        return results

    def format_as_snippet(self, memory) -> str:
        return self.snippet_template.format(
            source=memory.meta.source,
            title=memory.memory.title,
            context=memory.memory.context,
            content=memory.meta.content,
            start_line=memory.memory.start_line,
            end_line=memory.memory.end_line,
        )

    def print(self):
        print(self.get_content_summary())

    def get_content_summary(self, memories=None):
        memories = memories or self.memories
        summary = ""
        # group by source
        memories_by_source = {}
        for memory in memories:
            if memory.meta.scope == "root":
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
        # /temp
        try:
            with open(os.path.join(memory_dir, "ingested_hashed.json"), "r") as f:
                ingested_hashed = json.load(f)
                for key, hash in ingested_hashed.items():
                    if any([i.meta.source == key for i in self.memories]):
                        self.ingested_hashed[key] = hash
        except:
            pass
        self.memories = [MemoryWithMeta(**i) for i in memories]
        self.auto_save_dir = memory_dir
    
    def reload(self):
        self.load(self.auto_save_dir)

    def find_memory_tool(self):
        @tool()
        async def find_memory(
            question: str = Field(..., description="The question to search for."),
            num_results: int = Field(
                5,
                description="The number of raw memories to return or consider before answering. The results are ranked by relevance.",
            )
        ):
            """Search memories related to a question."""
            results = await self.retrieve(question, num_results=num_results)
            if len(results) == 0:
                return f"No memories found for question: {question}"
            result = "\n\n".join([self.format_as_snippet(i) for i in results])
            return result

        def register_message_handler(message_handler):
            self.register_message_handler(message_handler)
            find_memory.message_handler = message_handler

        find_memory.register_message_handler = register_message_handler

        return find_memory

    def ingest_tool(self):
        @tool()
        async def create_memories_from_file(
            path: str = Field(
                ...,
                description="The path to the dir or file to ingest. If a dir is provided, all files in the dir are ingested. If memories already exist, they are updated.",
            )
        ):
            """Read a file and create memories from it."""
            if not os.path.exists(path):
                _, error = open_or_search_file(path)
                return f"Error: {error}"
            new_memories = await self.ingest_rec(path)
            summary = self.get_content_summary(new_memories)
            return f"Ingested {path}. New memories formed:\n{summary} "

        def register_message_handler(message_handler):
            self.register_message_handler(message_handler)
            create_memories_from_file.message_handler = message_handler

        create_memories_from_file.register_message_handler = register_message_handler

        return create_memories_from_file

async def main():
    memory = SemanticParagraphMemory()
    memory.load(".minichain/memory")
    print(memory.get_content_summary())
    print(memory.get_content_summary())
    while (query := input("Query: ")) not in ["q", "quit", "exit", "stop" ]:
        results = await memory.retrieve(query)
        print("\n\n".join([memory.format_as_snippet(i) for i in results]))
        print([i.memory.title for i in results])
    
    breakpoint()




if __name__ == "__main__":
    import asyncio
    asyncio.run(main())