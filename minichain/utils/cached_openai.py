import openai
from retry import retry

from minichain.utils.disk_cache import disk_cache


def debug(f):
    def debugged(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            print(type(e), e)
            breakpoint()
            f(*args, **kwargs)

    return debugged


@disk_cache
@debug
@retry(tries=3, delay=1)
def get_openai_response(
    chat_history, functions, model="gpt-3.5-turbo-16k"
) -> str:  # "gpt-4-0613"
    messages = []
    for i in chat_history:
        message = i.dict()
        # delete the parent field
        message.pop("parent", None)
        # delete all fields that are None
        message = {k: v for k, v in message.items() if v is not None or k == "content"}
        messages.append(message)

    if len(functions) > 0:
        completion = openai.ChatCompletion.create(
            model=model,
            messages=messages,
            functions=functions,
            temperature=0.1,
        )
    else:
        completion = openai.ChatCompletion.create(
            model=model,
            messages=messages,
            temperature=0.1,
        )
    message = completion.choices[0].message
    return message.to_dict_recursive()

