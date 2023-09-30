import json
import os

import numpy as np
import openai
from retry import retry
from typing import Optional, Dict, Any

from minichain.utils.debug import debug
from minichain.utils.disk_cache import async_disk_cache, disk_cache
from minichain.dtypes import FunctionCall, AssistantMessage
from minichain.streaming import Stream


def parse_function_call(function_call: Optional[Dict[str, Any]]):
    if function_call is None:
        return None
    try:
        function_call["arguments"] = json.loads(function_call["arguments"])
        return FunctionCall(**function_call)
    except:
        pass
    if '"code": ```' in function_call["arguments"]:
        # replace first occurrence of ``` with " and last
        try:
            before, after = function_call["arguments"].split('"code": ```', 1)
            try:
                code, after = after.rsplit("```,", 1)[0]
            except:
                code, after = after.rsplit("```", 1)[0]
            arguments_no_code = json.loads(before + after)
            arguments = {"code": code, **arguments_no_code}
            function_call["arguments"] = arguments
            return FunctionCall(**function_call)
        except Exception as e:
            print(e)
            breakpoint()
    
    if '"code": `' in function_call["arguments"]:
        try:
            # replace first occurrence of ``` with " and last
            before, after = function_call["arguments"].split('"code": `', 1)
            if "`, " in after:
                try:
                    code, after = after.rsplit("`,", 1)[0]
                except:
                    code, after = after.rsplit("`", 1)[0]
            arguments_no_code = json.loads(before + after)
            arguments = {"code": code, **arguments_no_code}
            function_call["arguments"] = arguments
            return FunctionCall(**function_call)
        except Exception as e:
            print(e)
            breakpoint()
    
    if function_call['name'] == "python":
        # Somehow with python we get a string instead of a dict, which is probably easier for the model to handle, so we support it
        try:
            arguments = json.loads(function_call['arguments'])
        except:
            arguments = {"code": function_call['arguments']}
        function_call['arguments'] = arguments

    return FunctionCall(**function_call)


def fix_common_errors(response: Dict[str, Any]) -> AssistantMessage:
    """Fix common errors in the formatting and turn the dict into a AssistantMessage"""
    if not response.get("function_call"):
        response["function_call"] = {
            "name": "return",
            "arguments": json.dumps({"content": response.pop("content")}),
        }
        response["content"] = ""
    response["function_call"] = parse_function_call(response["function_call"])
    return AssistantMessage(**response)


def messages_types_to_history(chat_history: list) -> list:
    if not isinstance(chat_history[0], dict):
        messages = []
        for i in chat_history:
            # print(i)
            message = i.dict()
            # delete the parent field
            messages.append(message)
    else:
        messages = chat_history
    
    # remove function calls from messages if they are None
    for message in messages:
        message.pop("parent", None)
        message.pop("id", None)
        message.pop("conversation_id", None)
        # delete all fields that are None
        for k, v in dict(**message).items():
            if v is None and not k == "content":
                message.pop(k)
        if (function_call := message.get("function_call")) is not None:
            try:
                if isinstance(function_call['arguments'], dict):
                    function_call['arguments'] = json.dumps(function_call['arguments'])
            except Exception as e:
                print(e)
                breakpoint()
    return messages


def save_llm_call_for_debugging(messages, functions, response):
    os.makedirs(".minichain/debug", exist_ok=True)
    with open(".minichain/debug/last_openai_request.json", "w") as f:
        json.dump(
            {
                "messages": messages,
                "functions": functions,
                "response": response.dict(),
            },
            f,
        )


@async_disk_cache
# @retry(tries=10, delay=2, backoff=2, jitter=(1, 3))
async def get_openai_response_stream(
    chat_history, functions, model="gpt-4-0613", stream=None
) -> str:  # "gpt-4-0613", "gpt-3.5-turbo-16k"
    if stream is None:
        stream = Stream()
    messages = messages_types_to_history(chat_history)

    if len(functions) > 0:
        openai_response = openai.ChatCompletion.create(
            model=model,
            messages=messages,
            functions=functions,
            temperature=0.1,
            stream=True,
        )
    else:
        openai_response = openai.ChatCompletion.create(
            model=model,
            messages=messages,
            temperature=0.1,
            stream=True,
        )

    # iterate through the stream of events
    for chunk in openai_response:
        chunk = chunk["choices"][0]["delta"].to_dict_recursive()
        await stream.chunk(chunk)
    response = {key: value for key, value in stream.current_message.items() if "id" not in key}
    response = fix_common_errors(response)
    await stream.set(response)
    save_llm_call_for_debugging(messages, functions, response)
    return response


@disk_cache
@retry(tries=10, delay=2, backoff=2, jitter=(1, 3))
@debug
def get_embedding(text):
    response = openai.Embedding.create(model="text-embedding-ada-002", input=text)
    return np.array(response["data"][0]["embedding"])
