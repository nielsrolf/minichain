from minichain.agent import Agent, SystemMessage
from minichain.tools.google_search import google_search_function
from minichain.tools.recursive_summarizer import long_document_qa


def test_google_search():
    agent = Agent(
        functions=[google_search_function, long_document_qa],
        system_message=SystemMessage("Use google to search the web for a query."),
        prompt_template="{query}".format,
        on_assistant_message=lambda message: print(message),
        on_user_message=lambda message: print(message),
        on_function_message=lambda message: print(message),
    )
    query = "What is the capital of France?"
    result = agent.run(query=query)
    print(result)
