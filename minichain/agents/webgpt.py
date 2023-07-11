from minichain.agent import Agent, Function, FunctionMessage, SystemMessage
from minichain.tools.google_search import google_search_function
from minichain.tools.recursive_summarizer import long_document_qa
from minichain.memory import SemanticParagraphMemory

memory = SemanticParagraphMemory()

webgpt = Agent(
    functions=[google_search_function, memory.read_website, memory.recall],
    system_message=SystemMessage("You are webgpt. You research by using google search, reading websites, and recalling memories of websites you read. Once you gathered enough information, you end the conversation by answering the question."),
    prompt_template="{query}".format,
    onAssistantMessage=lambda message: print(message),
    onUserMessage=lambda message: print(message),
    onFunctionMessage=lambda message: print(message),
)


def test_webgpt():
    query = "What is the latest version of python?"
    result = webgpt.run(query=query)
    print(result)
    breakpoint()


if __name__ == "__main__":
    test_webgpt()