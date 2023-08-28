import json

import numpy as np
import openai
from retry import retry

from minichain.utils.debug import debug
from minichain.utils.disk_cache import async_disk_cache, disk_cache


def validate_message(message):
    if function := message.get("function_call"):
        try:
            json.loads(function["arguments"])
            return True
        except:
            return False
    return True


@async_disk_cache
# @retry(tries=10, delay=2, backoff=2, jitter=(1, 3))
async def get_openai_response_stream(
    chat_history, functions, model="gpt-4-0613", stream=lambda x: None
) -> str:  # "gpt-4-0613", "gpt-3.5-turbo-16k"
    try:
        messages = []
        # transform objects to dicts
        if not isinstance(chat_history[0], dict):
            for i in chat_history:
                print(i)
                message = i.dict()
                # delete the parent field
                message.pop("parent", None)
                message.pop("id", None)
                # delete all fields that are None
                message = {
                    k: v for k, v in message.items() if v is not None or k == "content"
                }
                messages.append(message)
        else:
            messages = chat_history

        # remove function calls from messages if they are None
        for i in messages:
            if i.get("function_call") is None:
                i.pop("function_call", None)

        # with open("last_openai_request.json", "w") as f:
        #     json.dump(
        #         {
        #             "messages": messages,
        #             "functions": functions,
        #         },
        #         f,
        #     )

        # print(messages[-2])
        # print("=====================================")
        if len(functions) > 0:
            response = openai.ChatCompletion.create(
                model=model,
                messages=messages,
                functions=functions,
                temperature=0.1,
                stream=True,
            )
        else:
            response = openai.ChatCompletion.create(
                model=model,
                messages=messages,
                temperature=0.1,
                stream=True,
            )

        # create variables to collect the stream of chunks
        collected_chunks = []
        collected_messages = []
        # iterate through the stream of events
        function_call = {}
        content = ""
        for chunk in response:
            collected_chunks.append(chunk)  # save the event response
            chunk = chunk["choices"][0]["delta"]  # extract the message
            collected_messages.append(chunk)  # save the message
            if "function_call" in chunk:
                delta = chunk["function_call"]
                for key, value in delta.items():
                    function_call[key] = function_call.get(key, "") + value
            if "content" in chunk:
                content += chunk["content"] or ""
            response = {
                "role": "assistant",
                "content": content,
            }
            if function_call != {}:
                response["function_call"] = function_call
            await stream(response)

        # if 'arguments' in function_call:
        #     try:
        #         function_call['arguments'] = json.loads(function_call['arguments'])
        #     except:
        #         print("Error parsing arguments", function_call['arguments'])
        # with open(f"last_openai_response_{len(messages)}.json", "w") as f:
        #     json.dump(
        #         {
        #             "response": response,
        #         },
        #         f,
        #     )

        return response
    except Exception as e:
        print(e)
        print(chat_history)


@disk_cache
@retry(tries=10, delay=2, backoff=2, jitter=(1, 3))
@debug
def get_embedding(text):
    response = openai.Embedding.create(model="text-embedding-ada-002", input=text)
    return np.array(response["data"][0]["embedding"])
