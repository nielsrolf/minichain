import pickle
import os
import pandas as pd


def get_all_cached_examples(cache_path=".cache"):
    data = []

    keys = [
        "disk_cache_object",
        "disk_cache_args",
        "disk_cache_kwargs",
    ]
    for file in os.listdir(cache_path):
        if file.endswith(".pkl"):
            with open(os.path.join(cache_path, file), "rb") as f:
                i = pickle.load(f)
                if isinstance(i, dict) and all(k in i for k in keys):
                    for k, v in i["disk_cache_kwargs"].items():
                        i[k] = v
                    data.append(i)
    return pd.DataFrame(data)


def find_all_caches(root="."):
    for root, dirs, files in os.walk(root):
        if ".cache" in dirs:
            yield os.path.join(root, ".cache")


def extract_all_conversations(df):
    conversations = []
    for _, row in df.iterrows():
        try:
            history = row.disk_cache_args[0]
            messages = [i.dict() for i in history]
            functions = row.disk_cache_args[1]
            response = row.disk_cache_object
            conversations.append(
                {
                    "history": messages,
                    "functions": functions,
                    "response": response,
                    "num_messages": len(messages),
                }
            )
        except Exception as e:
            print(e)
            # breakpoint()
            pass
    return conversations


if __name__ == "__main__":
    dfs = []
    for cache_path in find_all_caches():
        print(cache_path)
        try:
            df = get_all_cached_examples(cache_path)
            print(df.info())
            print(df.head())
            print(df.describe())
            dfs.append(df)
        except Exception as e:
            print(e)
            print("-" * 100)
    df = pd.concat(dfs)
    print(df.info())

    conversations = extract_all_conversations(df)
    num_messages = sum(i["num_messages"] for i in conversations)

    breakpoint()
    # df = get_all_cached_examples()
    # print(df.info())
    # print(df.head())
    # print(df.describe())
    # breakpoint()