import tiktoken


def split_recursively(text, split_at=["\n"], max_length=1000):
    if split_at == []:
        return [text]
    splits = []
    for i in text.split(split_at[0]):
        if len(tiktoken.encoding_for_model("gpt-3.5-turbo").encode(i)) > max_length:
            # split finer using the next token
            # print("splitting finer:", i)
            splits += split_recursively(i, split_at[1:])
        else:
            splits.append(i + split_at[0])
    return splits


def split_document(
    text, tokens=1000, overlap=100, split_at=["\n\n", "\n", ".", "?", "!"]
):
    total_tokens = len(tiktoken.encoding_for_model("gpt-3.5-turbo").encode(text))
    if total_tokens < tokens:
        return [text]
    # total_words = len(text.split())
    # if total_words < words:
    #     return [text]
    splits = split_recursively(text, split_at, tokens)
    # make sure no split is longer than the max length
    idx = 0
    while idx < len(splits):
        i = splits[idx]
        if len(tiktoken.encoding_for_model("gpt-3.5-turbo").encode(i)) > tokens:
            # force split every overlap words
            finer_split = []
            for j in range(0, len(i.split(" ")), overlap):
                finer_split.append(" ".join(i.split()[j : j + overlap]))
            # replace the split with the finer split
            splits = splits[:idx] + finer_split + splits[idx + 1 :]
            idx += len(finer_split) - 1
        idx += 1

    merged_splits = []
    current_chunk = ""
    while len(splits) > 0:
        current_split = splits.pop(0)

        # Add the split to the current chunk
        current_chunk += current_split

        # If the current chunk is full, add the chunk to the list of merged splits and start a new chunk
        if len(tiktoken.encoding_for_model("gpt-3.5-turbo").encode(current_chunk)) > tokens - overlap:
            merged_splits.append(current_chunk)
            if len(current_split.split()) <= overlap:
                current_chunk = current_split
            else:
                current_chunk = "..." + " ".join(current_split.split()[-overlap:])
    return merged_splits
