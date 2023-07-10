from minichain.utils.document_splitter import split_document
from minichain.utils.markdown_browser import markdown_browser

from minichain.agents import summarizer_function, qa_function


url = "https://en.wikipedia.org/wiki/Russia"
# website = markdown_browser(url)
# paragraphs = split_document(website)
# print([len(i.split()) for i in paragraphs])
# breakpoint()
# for paragraph in paragraphs:
#     print(paragraph)
#     print("---"*40)
#     print("---"*40)

# breakpoint()


def recursive_summarizer(text, question=None, max_words=500, summarize_at_least_once=False):
    if len(text.split()) < max_words and not summarize_at_least_once:
        return text
    else:
        if question is None:
            summary = summarizer_function(text=text)
        else:
            summary = qa_function(text=text, question=question)
        return recursive_summarizer(summary, max_words=max_words, question=question)


def recursive_web_summarizer(url, question=None, max_words=500):
    website = markdown_browser(url)
    paragraphs = split_document(website)
    while len(paragraphs) > 1:
        # print("splitting paragraphs:", [len(i.split()) for i in paragraphs])
        summaries = [recursive_summarizer(i, max_words=max_words, question=question) for i in paragraphs]
        joint_summary = "\n\n".join(summaries)
        # remove leading and trailing newlines
        summarize_at_least_once = len(summaries) > 1
        joint_summary = joint_summary.strip()
        paragraphs = split_document(joint_summary)
    return recursive_summarizer(paragraphs[0], max_words=max_words, question=question, summarize_at_least_once=summarize_at_least_once)



summary = recursive_web_summarizer(url, "what was the role of russia in world war 2?")
print(summary)
