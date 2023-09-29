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
