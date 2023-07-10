from minichain.utils.document_splitter import split_document
from minichain.utils.markdown_browser import markdown_browser

from minichain.agents import summarizer_function


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


def recursive_summarizer(text, question=None, max_words=500):
    if len(text.split()) < max_words:
        return text
    else:
        summary = summarizer_function(text=text, question=question)
        print(len(text.split()), "->", len(summary.split()))
        return recursive_summarizer(summary, max_words=max_words)


def recursive_web_summarizer(url, question=None, max_words=500):
    website = markdown_browser(url)
    paragraphs = split_document(website)
    while len(paragraphs) > 1:
        print("splitting paragraphs:", [len(i.split()) for i in paragraphs])
        summaries = [recursive_summarizer(i, max_words=max_words, question=question) for i in paragraphs]
        joint_summary = "\n\n".join(summaries)
        breakpoint()
        paragraphs = split_document(joint_summary)
    return recursive_summarizer(paragraphs[0], max_words=max_words, question=question)



summary = recursive_web_summarizer(url, "what was the role of russia in world war 2?")
print(summary)
