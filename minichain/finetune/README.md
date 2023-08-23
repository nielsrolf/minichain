# Finetuning OSS LLMs for minichain

## Data sources
- cached gpt-4 usage in minichain
- from github repo


## Github repo finetuning
Idea: use the commit history of a github repo. For each commit, generate train data that looks as if the commit had been written by minichain.

```
repo = GithubTrainer("nielsrolf/minichain")
conversation = repo.random_commit().as_conversation()
```
Conversation will have:
- the standard programmer system message
- the auto generated context
- each file diff as an edit function call

## RL for external memory using Github repo finetuning
```
repo = GithubTrainer("nielsrolf/minichain")
commit = repo.random_commit()

memories = Programmer().learn(commit)
score = Programmer().get_likelihood(commit.before, memories, commit.diff)
```