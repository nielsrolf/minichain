from perplexity_api import PerplexityAPI, TimeoutException
ppl = PerplexityAPI()

queries = [
    "hello world in python",
    "and in c++",
]

for i, query in enumerate(queries):
    if i > 0:
        print("***")
    print(query)
    print("***")
    try:
        print(ppl.query(query, follow_up=True))
    except TimeoutException:
        print("Query timed out:", query)
