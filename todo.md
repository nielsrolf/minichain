# todo
- codebase tool

# small things
- always return response, self in run_until_done
- code_interpreter: run files in /tmp and return files from /tmp/ ./outputs as structured data
- add ask_for_permission callback to Function
- make model configurable
- document how to override default logger for all agents


# bigger things

- Function: use openai decorators
- minichain.yml


# Maybe
- two step processes
    -examples:
        - edit (range) -> see current value -> write code in content -> function call returns
        - 
- give models the option to pipe the previous function result to the user to save tokens
- perplexity api tool as webgpt alternative









- add minichain.yml
    - websites it should learn
    - which model to use
    - where to cache
    - log level
    - which functions need permission
    - define command line agent
        - functions
        - system message


- game between agents:
    - game is a a function that has shared context between two agents
    - example:
        - write your name into winners.txt
        - make a coding challenge, solve it yourself, let opponents try to solve