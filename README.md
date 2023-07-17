
![`{mini: ⛓}`](logo.png)
<!-- # `{mini: ⛓}` -->

`{mini: ⛓}` is yet another langchain alternative: agents that understand and return structured data.

**Why?**
- structured output should be the default. Always converting to text is often a bottleneck
- langchain has too many classes and is generally too big.
- it's fun to build from scratch

**Core concepts**
The two core concepts are agents and functions that the agent can use. In order to respond, an an agent can use as many function calls as it needs until it uses the built-in return function that returns structured output.
Chat models are agents without structured output and end their turn by responding without a message that is not a function call. They return a string.

# Getting started

## Defining an agent
```python
from minichain.agent import Agent, SystemMessage
from minichain.memory import SemanticParagraphMemory
from minichain.tools.document_qa import AnswerWithCitations
from minichain.tools.google_search import google_search_function


memory = SemanticParagraphMemory()
webgpt = Agent(
    functions=[google_search_function, memory.read_website, memory.recall],
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
## Defining a tool

There are many use cases for wrapping agents inside of a function. This is currently a bit ugly and often looks like this:
```python
def tool(**inputs like schema): -> dict
    return outputs

tool_function = Function(
    name="tool",
    openapi=PydanticModel.schema()
) # dict like schema-> any dict

agent_with_tool = Agent(
    functions=[tool_dunction],
    response_format=PydanticResponseModel
) # .run(): dict like prompt_template_inputs -> dict like response_format
```

Longterm fixes:
- merge tool and tool_function via decorators
    ```
    @openai_function(description, ...)
    @input_field(type, ...)
    ```
- give function input and output schema


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
- [ ] bash:
    - [x] tool
    - [ ] use in agent
- [ ] python:
    - [ ] tool
    - [ ] use in agent
- [ ] CodeMemory
    - [x] util: generate_docs
    - tools
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


---
`{mini: ⛓}`