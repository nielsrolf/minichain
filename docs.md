<a id="agent"></a>

# agent

<a id="agent.Agent"></a>

## Agent Objects

```python
class Agent()
```

<a id="agent.Agent.run"></a>

#### run

```python
def run(**arguments)
```

arguments: dict with values mentioned in the prompt template

<a id="agent.Function"></a>

## Function Objects

```python
class Function()
```

<a id="agent.Function.__init__"></a>

#### \_\_init\_\_

```python
def __init__(openapi, name, function, description)
```

**Arguments**:

- `openapi` _dict_ - the openapi.json describing the function
- `name` _str_ - the name of the function
- `function` _any -> FunctionMessage_ - the function to call. Must return a FunctionMessage
- `description` _str_ - the description of the function

<a id="code_interpreter"></a>

# code\_interpreter

<a id="code_interpreter.python_function"></a>

#### python\_function

```python
def python_function(code)
```

executes the code and returns the result. Code can be an entire file or a snippet of code.

<a id="document_qa"></a>

# document\_qa

<a id="document_qa.qa"></a>

#### qa

```python
def qa(text, question, instructions=[])
```

Returns: a dict {content: str, citations: List[Citation]}}

<a id="recursive_summarizer"></a>

# recursive\_summarizer

<a id="recursive_summarizer.text_scan"></a>

#### text\_scan

```python
def text_scan(text, response_openapi, system_message)
```

Splits the text into paragraphs and asks the document_to_json agent for outouts.

<a id="text_to_memory"></a>

# text\_to\_memory

<a id="text_to_memory.text_to_memory"></a>

#### text\_to\_memory

```python
def text_to_memory(text, source=None) -> List[MemoryWithMeta]
```

Turn a text into a list of semantic paragraphs.
- add line numbers to the text
- Split the text into pages with some overlap
- Use an agent to create structured data from the text until it is done

<a id="replicate_client"></a>

# replicate\_client

<a id="replicate_client.get_model_details"></a>

#### get\_model\_details

```python
def get_model_details(model_id)
```

curl -s     -H "Authorization: Token $REPLICATE_API_TOKEN"     -H 'Content-Type: application/json'     "https://api.replicate.com/v1/models/{model_id}"

<a id="is_prompt_injection"></a>

# is\_prompt\_injection

<a id="is_prompt_injection.is_prompt_injection"></a>

#### is\_prompt\_injection

```python
def is_prompt_injection(text)
```

Check if the text is a prompt injection by feeding it to an agent that should always respond with a hard-coded response,
and see if the agent does this successfully.

