# todo
- perplexity api tool as webgpt alternative

Random:
- Function: use openai decorators

- summarize code: add instruction to use symbol identifiers as tags

- add ask_for_permission callback to Function
- add with minichain.default_logging(logging_function) context manager

- add `keep_session` for agents that should not create a session clone for follow up conversation. On follow up, respond without structured response (via `.chat` method)



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