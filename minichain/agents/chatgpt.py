from minichain.agent import Agent, SystemMessage


if __name__ == "__main__":
    chatgpt = Agent(
        [],
        system_message = SystemMessage(
            "You are chatgpt. You are a helpful assistant."
        ),
        prompt_template="{query}".format,
        silent=True
    )
    
    # Using elementary.audio, can you implement a new React component called SyncedAudioStemPlayer that plays a list of stems in a synced loop? The stems are specified by a public URL and need to be loaded into the virtual file system first
    # Can you show me how to use this component in an example?

    while query := input("# User: \n"):
        response = chatgpt.run(query=query, keep_session=True)
        print("# ChatGPT:\n", response)
