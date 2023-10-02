from minichain.agent import Agent


async def summarize(text, instructions=[]):
    system_message = f"Summarize the the text provided by the user. Do not start the summary with 'The text provided by the user' or similar phrases. Summarize by generating a shorter text that has the most important information from the text provided by the user."
    system_message += (
        "\n\n"
        + "Ignore parts of a website that are not content, such as navigation bars, footers, sidebars, etc. Respond only with the word 'skip' if the text consists of only these parts."
    )
    if instructions and len(instructions) > 0:
        system_message += "\n" + "\n".join(instructions)
    summarizer = Agent(
        functions=[],
        system_message=system_message,
        prompt_template="{text}".format,
    )
    summary = await summarizer.run(text=text)
    summary = summary["content"]
    if summary.lower() == "skip":
        summary = ""
    return summary
