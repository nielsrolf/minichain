from minichain.agent import Agent, SystemMessage
from minichain.memory import SemanticParagraphMemory
from minichain.tools.document_qa import AnswerWithCitations
from minichain.tools.google_search import google_search_function

memory = SemanticParagraphMemory()



webgpt = Agent(
    functions=[google_search_function, memory.read_website, memory.recall],
    system_message=SystemMessage(
        "You are webgpt. You research by using google search, reading websites, and recalling memories of websites you read. Once you gathered enough information, you end the conversation by answering the question. You cite sources in the answer text as [1], [2] etc."
    ),
    prompt_template="{query}".format,
    response_openapi=AnswerWithCitations,
)


if __name__ == "__main__":
    response = webgpt.run(query="In elementary.audio, how can I play an audio file from s3 using the virtual file system?")
    print(response)
    breakpoint()
