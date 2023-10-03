import pandas as pd
import requests


def check_api_state():
    endpoint = "http://localhost:8745/history"

    # Get all events
    events = requests.get(endpoint).json()
    childrenOf = events["childrenOf"]
    messages = pd.DataFrame(events["messages"])
    # set id as index
    messages = messages.set_index("id")
    parentOf = {}
    for parent, children in childrenOf.items():
        for child in children:
            parentOf[child] = parent

    breakpoint()

    while id := input("enter an id: "):
        try:
            print(messages.loc[id])
            # find the index of the message

        except KeyError:
            pass
        try:
            print("parent:", parentOf[id])
        except KeyError:
            print("no parent")
            pass
        try:
            print("children:", childrenOf[id])
        except KeyError:
            pass
        print("-" * 80)


def check_messages():
    import json

    events = []
    path = ".minichain/messages"
    last_valid = -1
    current = -1
    while current > last_valid - 10:
        current += 1
        try:
            with open(f"{path}/{current}.json", "r") as f:
                events.append(json.load(f))
                events[-1]["filename"] = f"{path}/{current}.json"
        except FileNotFoundError:
            break
    messages = {}
    stacks = {}
    for i, event in enumerate(events):
        if event.get("type", None) == "stack":
            stacks[event["stack"][-1]] = event
        else:
            messages[event["id"]] = event

    while id := input("enter an id: "):
        try:
            print("Message", messages[id])
        except KeyError:
            pass
        try:
            print("Stack\n", stacks[id])
        except KeyError:
            pass
        print("-" * 80)
    breakpoint()


check_messages()
