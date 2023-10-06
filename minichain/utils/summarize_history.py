import json

import tiktoken

from minichain.dtypes import FunctionCall, SystemMessage
from minichain.schemas import ShortenedHistory


def count_tokens(text):
    encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
    num_tokens = len(encoding.encode(text))
    return num_tokens


async def summarize_chunk(history):
    from minichain.agent import Agent

    prompt = ""
    for i, message in enumerate(history):
        prompt += f"Message {i}: {json.dumps(message)}\n"

    example = FunctionCall(
        name="return",
        arguments=json.dumps(
            {
                "messages": [
                    {"original_message_id": 0},
                    {"summary": "This is a summary of messages 2-6"},
                    {"original_message_id": 7},
                ]
            }
        ),
    )

    prompt += (
        "\n\nReturn the messages you want to keep with summaries for the less relevant messages by using the return function. Specify the shortened history like in this example:\n"
        + json.dumps(example.dict(), indent=2)
    )

    with open(".minichain/last_summarize_prompt", "w") as f:
        f.write(prompt)

    summarizer = Agent(
        functions=[],
        system_message=SystemMessage(history_summarize_prompt),
        prompt_template="{prompt}".format,
        response_openapi=ShortenedHistory,
    )

    summary = await summarizer.run(prompt=prompt)
    print(summary)

    new_history = []
    for keep in summary["messages"]:
        if keep["original_message_id"] is not None:
            new_history.append(history[keep["original_message_id"]])
        else:
            new_history.append(
                {
                    "role": "assistant",
                    "content": f"(summarized):\n{keep['summary']}",
                }
            )
    with open(".minichain/last_summary.json", "w") as f:
        json.dump(
            {"history": history, "summary": summary, "new_histrory": new_history}, f
        )
    return new_history


history_summarize_prompt = (
    "Summarize the following message history:\n"
    "- each message is presented in the format: 'Message <id>: <message json>'\n"
    "- you are the assistant. Formulate the summaries in first person, e.g. 'I did this and that.'\n"
    "- your task is to construct a shorter version of the message history that contains all relevant information that is needed to complete the task\n"
    "- you must keep every system message (role: system)"
    "- summarize steps related to completed tasks, but mention the full paths to all files that were created or modified\n"
    "- don't shorten it too much - you will in the next step be asked to continue the task with only the information you are keeping now. Details especially in the code are important. For tasks that are completed, you can remove the messages but add a summary that lists all the file paths you (assistant) worked on. \n"
    "- keep in particular the last messages that contain relevant details about the next steps.\n"
    "- you should try to shorten the history by about 50% and reduce the number of messages by at least 1\n"
    "- end the history in a way that makes it very clear what should be done next, and make sure all the information needed to complete the task is there\n"
)


async def get_summarized_history(messages, functions, max_tokens=6000):
    if messages[0]["content"] == history_summarize_prompt:
        # We are the summarizer, if we summarize at this point we go into an infinite loop
        return messages

    original_history = list(messages)
    print("original history", len(original_history))
    tokens = count_tokens(json.dumps(functions))
    assert tokens < max_tokens, f"Too many tokens in functions: {tokens} > {max_tokens}"
    # while the total token number is too large, we summarize the first max_token/2 messages and try again
    step = 1
    function_tokens = count_tokens(json.dumps(functions))
    while count_tokens(json.dumps(messages)) + function_tokens > max_tokens:
        print(
            "TOKENS",
            count_tokens(json.dumps(messages)) + function_tokens,
            function_tokens,
            max_tokens,
        )
        print("step", step)
        # Get as many messages as possible without exceeding the token limit. We first summarize only the first 75%, if that was not enough we summarize 87.5%, 93.75%, ...
        for i in range(1, len(messages)):
            if count_tokens(json.dumps(messages[:i])) > (
                max_tokens - function_tokens
            ) * (1 - 0.5 ** (step + 1)):
                break
        step += 1
        # Try to summarize the chunk until we get a summary that is smaller than the chunk. If we fail, increase the chunk size and try again
        tokens_to_summarize = count_tokens(json.dumps(messages[:i]))
        summary = await summarize_chunk(messages[:i])
        summarized_tokens = count_tokens(json.dumps(summary))

        print("CHUNK TOKENS", tokens_to_summarize)
        print("MAYBE FAILED?", summarized_tokens, "/", tokens_to_summarize)
        if summarized_tokens > tokens_to_summarize:
            print("FAILED")
            breakpoint()
            continue  # with increased step, and therefore larger chunk
        breakpoint()
        messages = summary + messages[i:]

    if messages[-1]["content"].startswith("(summarized)"):
        messages[-1]["content"] += "\n\nOkay let's continue with the task."

    with open(".minichain/last_summarized_history_final.json", "w") as f:
        json.dump(
            {
                "original_history": original_history,
                "summarized_history": messages,
                "length_original": count_tokens(json.dumps(original_history)),
                "length_shortened": count_tokens(json.dumps(messages)),
            },
            f,
        )

    return messages
