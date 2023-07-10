from minichain.agent import Agent, SystemMessage, FunctionMessage, UserMessage, AssistantMessage, FunctionCall, Function
from minichain.utils.markdown_browser import markdown_browser
from minichain.memory import SemanticParagraphMemory
from minichain.utils.search import google_search






def summarize(text, question=None, instructions=[]):
    question_instruction = ""
    if question:
        question_instruction = "Focus the summary on information related to the following question: '{question}'. If the text contains no information related to the question, answer only with the word 'skip'. You may repeat sections of the text verbatim if they are very relevant.".format(question=question)
    system_message = f"Summarize the the text provided by the user. {question_instruction}Do not start the summary with 'The text provided by the user' or similar phrases. Summarize by generating a shorter text that has the most important information from the text provided by the user."
    system_message += "\n\n" + "Ignore parts of a website that are not content, such as navigation bars, footers, sidebars, etc. Respond only with the word 'skip' if the text consists of only these parts."
    if instructions and len(instructions) > 0:
        system_message += "\n" + "\n".join(instructions)
    summarizer = Agent(
        functions=[],
        system_message=SystemMessage(
            system_message
        ),
        prompt_template="{text}".format
    )
    summary = summarizer.run(text=text)
    if summary.content.lower() == "skip":
        summary.content = ""
    return summary
    

summarizer_function = Function(
    name="summarizer",
    openapi={
        "text": "string",
        "question": "string",
        # optionally provide a list of instructions on what to focus on
        "instructions": "list"
    },
    function=summarize,
    description="Summarize the the text provided by the user."
)


google_search_function = Function(
    name="google_search",
    openapi={
        "query": "string",
    },
    function=google_search,
    description="Use google to search the web for a query."
)









# # Web search: google search, read website, semantic search
# memory = SemanticParagraphMemory()
# web_search_agent = Agent(
#     functions=[
#         google_search,
#         memory.ingest,
#         memory.semantic_search,
#     ],
#     system_message=SystemMessage(
#         "You are a web search agent. You use google to discover initial websites, and you can read websites until you know enough to answer the question. You use function calls until you are done. The session ends when you answer with a message that does not include a function call."
#     ),
#     prompt_template="{query}".format
# )


# web_search_function = Function(
#     name="web_search",
#     openapi={
#         "query": "string",
#         "num_results": "int"
#     },
#     function=web_search_agent.run,
#     description="Search the web for a query, and read the websites until you know enough to answer the question. The session ends when you answer with a message that does not include a function call."
# )


# critical_thinking_agent = Agent(
#     functions=[],
#     system_message=SystemMessage(
#         "You are a critical thinking agent. The user message contains a question and a chain of thought to answer that question. You rate how solid the logic is. TODO"
#     ),
#     prompt_template="{query}".format
# )




# # Tree of thought agent
# def tree_of_thought_agent(base_agent, num_agents=3):
#     pass