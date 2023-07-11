from minichain.agent import Function
from minichain.tools.document_qa import qa_function
from minichain.tools.summarize import summarizer_function
from minichain.utils.document_splitter import split_document
from minichain.utils.markdown_browser import markdown_browser


def _recursive_summarizer(
    text, question=None, max_words=500, summarize_at_least_once=False
):
    if len(text.split()) < max_words and not summarize_at_least_once:
        return text
    else:
        if question is None:
            summary = summarizer_function(text=text)
        else:
            summary = qa_function(text=text, question=question)
        return _recursive_summarizer(summary, max_words=max_words, question=question)


def recursive_summarizer(text, question=None, max_words=500):
    paragraphs = split_document(text)
    summarize_at_least_once = True
    while len(paragraphs) > 1:
        # print("splitting paragraphs:", [len(i.split()) for i in paragraphs])
        summaries = [
            recursive_summarizer(i, max_words=max_words, question=question)
            for i in paragraphs
        ]
        joint_summary = "\n\n".join(summaries)
        # remove leading and trailing newlines
        summarize_at_least_once = len(summaries) > 1
        joint_summary = joint_summary.strip()
        paragraphs = split_document(joint_summary)
    return recursive_summarizer(
        paragraphs[0],
        max_words=max_words,
        question=question,
        summarize_at_least_once=summarize_at_least_once,
    )


def recursive_web_summarizer(url, question=None, max_words=500):
    website = markdown_browser(url)
    return recursive_summarizer(website, question=question, max_words=max_words)


long_document_summarizer = Function(
    name="long_document_summarizer",
    openapi={"text": "string", "question": "string", "max_words": "integer"},
    function=recursive_summarizer,
    description="Summarize a long document. Optionally provide a question to focus on a specific topic.",
)


# question = "what was the role of russia in world war 2?"
# url = "https://en.wikipedia.org/wiki/Russia"
# url = "https://www.tagesschau.de/ausland/putin-prigoschin-gespraech-100.html"

# question = "how can i play an audio file on a public s3 bucket using elementary audio?"
# url = "https://www.elementary.audio/docs/packages/web-renderer"

# summary = recursive_web_summarizer(url, question)
# print(summary)
# print(len(summary.split()))
