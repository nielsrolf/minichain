import tiktoken
import json


def count_tokens(chat_message: dict):
    """Counts the number of tokens in a chat message"""
    text = chat_message["content"]
    if (function_call := chat_message.get("function_call")) is not None:
        text += json.dumps(function_call)
    encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
    num_tokens = len(encoding.encode(text))
    print("Counted tokens:", num_tokens, "for message:", text[:100], "...")
    return num_tokens