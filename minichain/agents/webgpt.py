from typing import List, Optional

from pydantic import BaseModel, Field

from minichain.agent import Agent, Function, SystemMessage
from minichain.tools.document_qa import AnswerWithCitations
from minichain.tools.google_search import google_search_function
from minichain.tools.recursive_summarizer import text_scan
from minichain.tools.text_to_memory import Memory
from minichain.utils.markdown_browser import markdown_browser


class ScanWebsiteRequest(BaseModel):
    url: str = Field(..., description="The url to read.")
    question: str = Field(..., description="The question to answer.")


class RelevantSection(BaseModel):
    start_line: int = Field(..., description="The start line of this section (line numbers are provided in the beginning of each line).")
    end_line: int = Field(..., description="The end line of this section.")

class RelevantSectionOrClick(BaseModel):
    relevant_section: Optional[RelevantSection]
    click: Optional[str]


class Query(BaseModel):
    query: str = Field(..., description="The query to search for.")


def scan_website(url, question):
    website = markdown_browser(url)
    lines = website.split("\n")
    website_with_line_numbers = "\n".join(
        f"{i+1} {line}" for i, line in enumerate(lines)
    )

    outputs = text_scan(
        website_with_line_numbers,
        RelevantSectionOrClick,
        f"Scan the text provided by the user for sections relevant to the question: {question}. Save sections that contain a partial answer to the question. If the answer is not in the text, click on the link that is most likely to contain the answer and then return in the next turn. If no link is promising, return immediately.")
    sections = [
        {
            "content": "\n".join(lines[output['relevant_section']['start_line'] : output['relevant_section']['end_line']]),
            "source": url,
        }
        for output in outputs
        if output['relevant_section'] is not None
    ]
    clicks = [output['click'] for output in outputs if output['click'] is not None]
    if not url.startswith("http"):
        url = "https://" + url
    domain = "/".join(url.split("/")[:3]) # e.g. https://www.google.com
    clicks = [f"{domain}/{click}" for click in clicks if not click.startswith("http")]
    print("clicks:", clicks)
    return {
        "relevant_sections": sections,
        "read_next": clicks,
    }


scan_website_function = Function(
    name="scan_website",
    openapi=ScanWebsiteRequest,
    function=scan_website,
    description="Read a website and collect information relevant to the question, and suggest a link to read next.",
)


class WebGPT(Agent):
    def __init__(self, silent=False, **kwargs):
        super().__init__(
            functions=[google_search_function, scan_website_function],
            system_message=SystemMessage(
                "You are webgpt. You research by using google search, reading websites, and recalling memories of websites you read. Once you gathered enough information to answer the question or fulfill the user request, you end the conversation by answering the question. You cite sources in the answer text as [1], [2] etc."
            ),
            prompt_template="{query}".format,
            response_openapi=AnswerWithCitations,
            silent=silent,
            **kwargs,
        )


class SmartWebGPT(Agent):
    def __init__(self, silent=False, **kwargs):
        super().__init__(
            functions=[WebGPT(silent=silent).as_function("research", "Research the web in order to answer a question.", Query)],
            system_message=SystemMessage(
                "You are SmartGPT. You get questions or requests by the user ans answer them in the following way: \n" +
                "1. If the question or request is simple, answer it directly. \n" +
                "2. If the question or request is complex, use the 'research' function available to you \n" +
                "3. If the initial research was insufficient, use the 'research' function with new questions, until you are able to answer the question."
            ),
            prompt_template="{query}".format,
            response_openapi=AnswerWithCitations,
            silent=silent,
            **kwargs,
        )


if __name__ == "__main__":
    # webgpt = WebGPT()
    webgpt = SmartWebGPT(silent=True)
    
    # Using elementary.audio, can you implement a new React component called SyncedAudioStemPlayer that plays a list of stems in a synced loop? The stems are specified by a public URL and need to be loaded into the virtual file system first
    # Can you show me how to use this component in an example?

    while query := input("# User: \n"):
        response = webgpt.run(query=query, keep_session=True)
        print("# WebGPT:\n", response['content'])
        if len(response['citations']) > 0:
            print("Sources:", response['citations'])
        webgpt = response['session']
        print("")
