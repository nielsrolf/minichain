from minichain.agent import Agent, SystemMessage
from minichain.memory import SemanticParagraphMemory
from minichain.tools.document_qa import AnswerWithCitations
from minichain.tools.google_search import google_search_function





class Expert():
    """
    Expert agent that learns about topic using webgpt-memory and answers questions using the memory.
    
    Example usage:
    ```
    from minichain.agents.expert import Expert

    expert = Expert()
    expert.learn("learn the javascript API of elementary.audio")
    """
    def __init__(self, load_memory=".memory/"):
        memory = SemanticParagraphMemory()
        if load_memory:
            memory.load(load_memory)
        self.webgpt = Agent(
            functions=[google_search_function, memory.read_website, memory.recall],
            system_message=SystemMessage(
                "You are webgpt. You research by using google search, reading websites, and recalling memories of websites you read. Once you gathered enough information, you end the conversation by answering the question. You cite sources in the answer text as [1], [2] etc."
            ),
            prompt_template="{query}".format,
            response_openapi=AnswerWithCitations,
        )
        self.memory = memory
    
    def learn(self, query):
        questions = self.memory.generate_questions(query)
        learned = []
        first_addition = True
        for question in questions:
            response = self.webgpt.run(query=question)
            if first_addition:
                self.webgpt.system_message.content += "\n\nYou already learned the following:\n"
                first_addition = False
            self.webgpt.system_message.content += "\n" + str(AnswerWithCitations(**response))
            learned.append(response)
        return learned
    
    def ask(self, question):
        response = self.webgpt.run(query=question)
        return response



if __name__ == "__main__":
    expert = Expert()
    expert.learn("learn the javascript API of elementary.audio")
    while query := input("query: "):
        response = expert.ask(query)
        print(response.content)
        print(response.citations)
