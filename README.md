# Minichain

![logo](logo.png)

Agents that understand and return structured data.


# Docs
There are many use cases for wrapping agents inside of a function. This often looks like this:
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
) # .run(): prompt_template_inputs -> dict like response_format
```

## Longterm fixes:
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
    - [ ] adjust `Agent` to automatically retrieve relevant memories

### WebGPT
- [x] markdown browser
- [x] google search
- [x] Memory
- [ ] read_later tool

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