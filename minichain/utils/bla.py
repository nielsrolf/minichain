import openai
import json


# send a ChatCompletion request to count to 100
response = openai.ChatCompletion.create(
    model='gpt-3.5-turbo',
    messages=[
        {'role': 'user', 'content': 'send a message to Jackson'}
    ],
    functions=[
        {
            "name": "send_message",
            "description": "Send a message to another player.",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {
                        "type": "string",
                        "description": "list of names of the players you want to send a message to. Example: \"Sophia, John\"",
                    },
                    "message": {
                        "type": "string",
                        "description": "The message you want to send.",
                    },
                },
                "required": ["to", "message"],
            },
        }
    ],
    temperature=0,
    stream=True  # again, we set stream=True
)

def stream(message):
    # print(message)
    pass


# create variables to collect the stream of chunks
collected_chunks = []
collected_messages = []
# iterate through the stream of events
function_call = {}
content = ''
for chunk in response:
    collected_chunks.append(chunk)  # save the event response
    chunk = chunk['choices'][0]['delta']  # extract the message
    collected_messages.append(chunk)  # save the message
    if "function_call" in chunk:
        delta = chunk['function_call']
        for key, value in delta.items():
            function_call[key] = function_call.get(key, "") + value
    if "content" in chunk:
        content += chunk['content'] or ''
    stream({"role": "assistant", "content": content, "function_call": function_call})
function_call['arguments'] = json.loads(function_call['arguments'])
msg = {
    "role": "assistant",
    "content": content,
    "function_call": function_call
}

print(msg)