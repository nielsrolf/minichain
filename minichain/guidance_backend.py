import guidance

# define the chat model we want to use (must be a recent model supporting function calls)
guidance.llm = guidance.llms.OpenAI("gpt-3.5-turbo-0613", caching=False)

# define a guidance program that uses tools
program = guidance("""
{{~#system~}}
{{system}}
{{>tool_def functions=functions}}
{{~/system~}}

{{~#user~}}
Get the current weather in New York City.
{{~/user~}}

{{~#each range(10)~}}
    {{~#assistant~}}
    {{gen 'answer' max_tokens=50 function_call="auto"}}
    {{~/assistant~}}

    {{#if not callable(answer)}}{{break}}{{/if}}
    
    {{~#function name=answer.__name__~}}
    {{answer()}}
    {{~/function~}}
{{~/each~}}""")
                   

def get_openai_response(
    chat_history, functions, model="gpt-4-0613"
):
    pass
    