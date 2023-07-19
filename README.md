
![`{mini: ⛓}`](logo.png)
<!-- # `{mini: ⛓}` -->

`{mini: ⛓}` is a minimal langchain alternative for agents with structured data, and many tools for them. You only need one class: `Agent` - for chat, chat with tool usage, or acting as a function.

**Why?**
- structured output should be the default. Always converting to text is often a bottleneck
- langchain has too many classes and is generally too big.
- it's fun to build from scratch

**Core concepts**
The two core concepts are agents and functions that the agent can use. In order to respond, an an agent can use as many function calls as it needs until it uses the built-in return function that returns structured output.
Chat models are agents without structured output and end their turn by responding without a message that is not a function call. They return a string.

# Getting started


## Defining a tool

Define a tool using the `@tool()` decorator:
```python
from minichain.agent import Agent, SystemMessage, tool

@tool()
def scan_website(
    url: str = Field(..., description="The url to read.", ),
    question: str = Field(..., description="The question to answer.")
):
    ...
    return answer
```


## Defining an agent
```python
from minichain.agent import Agent, SystemMessage
from minichain.tools.document_qa import AnswerWithCitations
from minichain.tools.google_search import google_search_function

...

webgpt = Agent(
    functions=[google_search_function, scan_website],
    system_message=SystemMessage(
        "You are webgpt. You research by using google search, reading websites, and recalling memories of websites you read. Once you gathered enough information, you end the conversation by answering the question. You cite sources in the answer text as [1], [2] etc."
    ),
    prompt_template="{query}".format,
    on_assistant_message=lambda message: print(message),
    on_function_message=lambda message: print(message),
    response_openapi=AnswerWithCitations, # this is a pydantic.BaseModel
)

response = webgpt.run(query="What is the largest publicly known language model in terms of parameters?")
print(response['content'], response['sources'])
```



## Install
```
pip install -e .
```


---
## Roadmap
### Basics
- [x] `Agent` that uses tools and returns structured outputs 
- [x] utils:
    - `disk_cache`
    - `cached_openai`: for predictable and cheaper development
    - `docker_sandbox`
    - `markdown_browser`
    - `search`
    - `generate_docs`
    - `document_splitter`
### Memory
- [x] tools for long documents
    - [x] recursive summary
    - [x] recursive qa-summary
    - [x] `scan_text` to feed chunked text into agent
- [x] Semantic Paragraph Memory
    - [x] split documents into semantic paragraphs
    - [x] VectorDB search:
        - generate subquestions, embed them, compare with embeddings of `memory.relevant_questions`
    - [x] keyword search:
        - show list of memorized tags, generate list of tags to retrieve memories
    - [x] content_scan search:
        - Show a summary (titles, tags) of all memories. Use `scan_text` to select relevant memory titles
    - [x] tools to save and recall memories

### WebGPT
- [x] markdown browser
- [x] google search
- [x] document_qa_scan

### Expert
- [x] Memory
- [ ] init:
    - [x] generate subquestions -> 
    - [x] current webgpt
    - [ ] document_qa_scan: build a general context

### Programmer
- [x] bash
- [x] python
- [ ] Codebase
    - [x] util: generate_docs
    - tools
        - [ ] view file
        - [ ] edit file
        - [ ] get_package_summary
            - generate_docs + summarize(file)
        - [ ] lookup symbol (--show_full_code: False)
        - [ ] update symbol: replaces the code
        - [ ] code qa
            - use SemanticParagraphMemory
            - init it with symbol memories

### Multimodal replicate
- [ ] replicate search tool
- [ ] replicate import tool
- [ ] replicate run tool

### UI
- [ ] webui for local deployment
- [ ] VSCode integration

### Planning module
- [ ] Agent: planner is called every n steps / seconds
- [ ] Planner: tool to give feedback for a conversation
    - task board
    - return: {all good / message to refocus}
- [ ] output of the planner appears as a function message in the chat


