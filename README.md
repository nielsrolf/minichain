# Minichain

# Done
- recursive text summarizer
- long document qa
- is_prompt_injection

# WIP
- memory
- webgpt
- replicate_client

# Todo
- bash_user
- python_user
- textedit
- tree of thought


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

## Defining a function
The best way to define a function is to define a pydantic model that describes the input type for the function. Let's do this with the example of the `GoogleSearch` function:
```
class SearchQuery(BaseModel):
    query: str = Field(..., description="The query to search for.")


google_search_function = Function(
    name="google_search",
    openapi=SearchQuery,
    function=lambda search_query: google_search(search_query.query),
    description="Use google to search the web for a query."
)
```

## Defining an agent
```
todo
```
