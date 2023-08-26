<!-- # minichain -->
![`minichain`](logo.png)

`{mini: ⛓}` is a minimal langchain alternative for agents with structured data, and many tools for them. You only need one class: `Agent` - for chat, chat with tool usage, or acting as a function.

[![Demo video](https://img.youtube.com/vi/b0CbP-kUJt0/0.jpg)](https://www.youtube.com/watch?v=b0CbP-kUJt0)
-- demo of a programmer agent built with minichain, using the [VSCode extension ui](./minichain-vscode/)

**Why?**
- structured output should be the default. Always converting to text is often a bottleneck
- langchain has too many classes and is generally too big.
- it's fun to build from scratch

**Core concepts**
The two core concepts are agents and functions that the agent can use. In order to respond, an an agent can use as many function calls as it needs until it uses the built-in return function that returns structured output.
Chat models are agents without structured output and end their turn by responding without a message that is not a function call. They return a string.

# Getting started
To install the python library, run:
```
pip install git+git://github.com/nielsrolf/minichain
docker pull docker push nielsrolf/minichain:latest
```

## Defining a tool

Define a tool using the `@tool()` decorator:
```python
from minichain.agent import Agent, SystemMessage, tool

@tool()
async def scan_website(
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
In order to install the core python package, run:
```
pip install -e .
```

## Running tests
```
pytest test
```

## UI dev setup
The UI requires the backend to run:
```
python -m minichain.api
```
Then, install and start the frontend:
```
cd minichain-ui
npm install
npm run start
```



