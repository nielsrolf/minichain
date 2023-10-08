import json
import os
from typing import Any, Dict, Optional

import numpy as np
import openai
from retry import retry

from minichain.dtypes import AssistantMessage, FunctionCall
from minichain.message_handler import StreamCollector
from minichain.utils.debug import debug
from minichain.utils.disk_cache import async_disk_cache, disk_cache


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

    if function_call["name"] == "python":
        # Somehow with python we get a string instead of a dict, which is probably easier for the model to handle, so we support it
        try:
            arguments = json.loads(function_call["arguments"])
        except:
            arguments = {"code": function_call["arguments"]}
        function_call["arguments"] = arguments

    return FunctionCall(**function_call)


def fix_common_errors(response: Dict[str, Any]) -> Dict[str, Any]:
    """Fix common errors in the formatting and turn the dict into a AssistantMessage"""
    if not response.get("function_call"):
        response["function_call"] = {
            "name": "return",
            "arguments": json.dumps({"content": response.pop("content")}),
        }
        response["content"] = ""
    response["function_call"] = parse_function_call(response["function_call"])
    if "```" in response["content"] and response["function_call"]["name"] in ["python", "edit"]:
        # move the code to the arguments
        raw = response["content"]
        for language in ["python", "bash", "javascript", "html", "css", "json", "yaml", "sql", "markdown", "latex", "c", "cpp", "csharp", "go", "java", "kotlin", "php", "ruby", "rust", "scala", "swift", "py", "sh", "js"]:
            raw = raw.replace(f"```{language}", "```")
        content, code = raw.split("```\n", 1)
        response["content"] = content
        # remove the last ``` and everything after it
        try:
            if not ("\n```" in code):
                code, content_after = code.rsplit("```", 1)[0]
            else:
                code, content_after = code.split("\n```", 1)
        except:
            breakpoint()
        response["function_call"]["arguments"]["code"] = code
    return response


def format_history(messages: list) -> list:
    """Format the history to be compatible with the openai api - json dumps all arguments"""
    for message in messages:
        try:
            if (function_call := message.get("function_call")) is not None:
                if isinstance(function_call["arguments"], dict):
                    content = function_call["arguments"].pop("content", None)
                    message["content"] = content or message["content"]
                    code = function_call["arguments"].pop("code", None)
                    if code is not None:
                        message["content"] = message["content"] + f"\n```\n{code}\n```"
                    function_call["arguments"] = json.dumps(function_call["arguments"])
        except Exception as e:
            print(e)
            breakpoint()
    return messages


def save_llm_call_for_debugging(messages, functions, parsed_response, raw_response):
    try:
        os.makedirs(".minichain/debug", exist_ok=True)
        with open(".minichain/debug/last_openai_request.json", "w") as f:
            json.dump(
                {
                    "messages": messages,
                    "functions": functions,
                    "parsed_response": parsed_response,
                    "raw_response": raw_response,
                },
                f,
            )
    except Exception as e:
        print(e)
        breakpoint()


@async_disk_cache
@retry(tries=10, delay=2, backoff=2, jitter=(1, 3))
async def get_openai_response_stream(
    chat_history, functions, model="gpt-4-0613", stream=None
) -> str:  # "gpt-4-0613", "gpt-3.5-turbo-16k"
    if stream is None:
        stream = StreamCollector()
    messages = format_history(chat_history)

    try:
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
    except openai.error.RateLimitError as e:
        import time
        print("We got rate limited, chilling for a minute...")
        time.sleep(60)
        raise e
    except Exception as e:
        print(e)
        breakpoint()
    raw_response = {
        key: value for key, value in stream.current_message.items() if "id" not in key
    }
    response = fix_common_errors(raw_response)
    await stream.set(response)
    save_llm_call_for_debugging(
        messages, functions, response, raw_response=raw_response
    )
    return response


@disk_cache
@retry(tries=10, delay=2, backoff=2, jitter=(1, 3))
@debug
def get_embedding(text):
    response = openai.Embedding.create(model="text-embedding-ada-002", input=text)
    return np.array(response["data"][0]["embedding"])
