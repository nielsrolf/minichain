from minichain.agent import Agent, SystemMessage


class ChatGPT(Agent):
    def __init__(self, **kwargs):
        kwargs["functions"] = kwargs.get("functions", [])
        kwargs["system_message"] = kwargs.get(
            "system_message",
            "You are chatgpt. You are a helpful assistant.",
        )
        kwargs["prompt_template"] = "{query}".format
        super().__init__(**kwargs)


async def main():
    chatgpt = ChatGPT()
    while query := input("You: "):
        response = await chatgpt.run(query=query)
        print(response["content"])


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
