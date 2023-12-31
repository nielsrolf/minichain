
# minichain 
<img src='minichain-vscode/logo.png' width="100px"> 

Minichain is a framework for LLM agents with structured data, and useful tools for them. It consists of three components
- the [python `minichain` package](#python-package) to build agents that run on the host
- tools that allow agents to run, debug, and edit code, interact with frontend devtools, and a semantic memory creation and retrieval system that allow for infinitely long messages and conversations
- a webui that can be started in [docker](#web-ui) and used as a [vscode extension](#vscode-extension)

Checkout the [example use cases](#demo)

# Installation

If you want to use GPT powered agents as programming assistants in VSCode, install the VSCode extension and the minichain backend via docker.
To develop your own agents, install the python package.

## VSCode extension

The VSCode extension requires you to have a locally running backend - either started via [docker](#web-ui) or via [python](#python-package) - on `http://localhost:8745`.

You can install the VSCode extension by downloading the `.vsix` file from [releases](https://github.com/nielsrolf/minichain/releases).

To start the extension, you can open Visual Studio Code, go to the Extensions view (Ctrl+Shift+X), and click on the ... (More Actions) button at the top of the view and select Install from VSIX.... Navigate to the minichain-vscode/ directory, select the .vsix file, and click Install. After the installation, you should be able to use the "Open Minichain" command.

## Web-UI
If you want to use the UI (either via browser or with the VSCode extension), run:
```bash
cp .env.example .env # add your openai, replicate and serp API keys.
docker run -v $(pwd):$(pwd) \
     -w $(pwd) -p 20000-21000:20000-21000 -p 8745:8745 \
     --env-file .env \
     nielsrolf/minichain # optionally:  --gpus all 
```

You can then open minichain on [`http://localhost:8745/index.html`](http://localhost:8745/index.html). You will need the token printed in the beginning of the startup to connect.

# Demo

The demos are created using the "Share"-Button that gives read access to a workspace of conversation. In order actually talk to agents, you need to install minichain and use your own OpenAI API key. 
- **create and deploy a simple full stack app**: [demo](https://minichain.polybase.app/index.html?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJmcm9udGVuZCIsInNjb3BlcyI6WyIxMmFlMWYyYiIsInZpZXciXX0.GFcoM6lGzx6pK_qBxqs7jPFZxpWhYs99RseLcRUNiek)
    - creates a backend
    - starts it
    - creates a frontend
    - tests the frontend using "Chrome Devtools" as a function
    - finds and fixes some CORS issues
    - fixes the errors
- build and deploy a [simple portfolio website](https://minichain.polybase.app/.public/portfolio): [demo](https://minichain.polybase.app/index.html?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJmcm9udGVuZCIsInNjb3BlcyI6WyIzNDUxNTQ4OSIsInZpZXciXX0.PUS3QWVJQ07MIoLtpfwUgE2mdYTBVx0K07o8C_MHAh0)
- help as a research assistant: [demo](https://minichain.polybase.app/index.html?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJmcm9udGVuZCIsInNjb3BlcyI6WyIzMjMzMTVjOSIsInZpZXciXX0.jPrNeH5tsWXakhALjEPft7Gc81BTS1O_85DMboqPyHQ)
    - derive a loss function from an idea
    - solve the optimizatin problem using torch
    - visualize the results
- make a beautiful 3d plot to demonstrate the jupyter like environment: [demo](https://minichain.polybase.app/index.html?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJmcm9udGVuZCIsInNjb3BlcyI6WyJiOGZkNTRhYiIsInZpZXciXX0.To41pbcUND5Zwba8EVKuUR6-Wr7fWSaiVcxzkSQpQh0)
- working with messages that are longer than the context: [demo](https://minichain.polybase.app/index.html?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJmcm9udGVuZCIsInNjb3BlcyI6WyJiMmYwNGYyMyIsInZpZXciXX0.eG088GxE6g9ib_LW0oCXdhg6-ba7fGPyPUF3U0-fpEY)
    - for this example the context size was set to 2k
    - the messages is first ingested into semantic memories that can be accessed using the `find_memory` tool


[![Demo video](https://img.youtube.com/vi/wxj7qjC8Xb4/0.jpg)](https://www.youtube.com/watch?v=wxj7qjC8Xb4)

## Python package
If you want to build agents, install the python library:
```bash
pip install git+https://github.com/nielsrolf/minichain
cp .env.example .env # add your openai, replicate and serp API keys.
```

It is recommended to run agents inside of docker environments where they have no permission to destroy important things or have access to all secrets. If you feel like taking the risk, you can also run the api on the host via: `python -m minichain.api`.



# Python library
**Why?**
- structured output should be the default. Always converting to text is often a bottleneck
- langchain has too many classes and is generally too big.
- it's fun to build from scratch

**Core concepts**
The two core concepts are agents and functions that the agent can use. In order to respond, an an agent can use as many function calls as it needs until it uses the built-in return function that returns structured output.
Chat models are agents without structured output and end their turn by responding without a message that is not a function call. They return a string.


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
    response_openapi=AnswerWithCitations, # this is a pydantic.BaseModel
)

response = await webgpt.run(query="What is the largest publicly known language model in terms of parameters?")
print(response['content'], response['sources'])
```

## Running tests
```
pytest test
```

