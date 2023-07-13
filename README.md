# Minichain

Agents that understand and return structured data.

## Overview
- core: Agent, Function
- memory
- utils:
    - disk_cache
    - cached_openai
    - docker_sandbox
    - markdown_browser
    - search
    - generate_docs
    - document_splitter
- tools:
    - bash_user
    - code_interpreter
    - document_qa
    - summarize
    - recursive_summarizer:
        - long_document_summarizer
        - long_document_qa
        - scan_text
    - is_prompt_injection
    - text_to_memory
    - google_search
- agents
    - webgpt
    - programmer
    - replicate_multimodal



# Docs
There are many use cases for wrapping agents inside of a function. This often looks like this:
```
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

