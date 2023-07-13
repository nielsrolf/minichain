# todo

- text_to_memory.py:
    - add links to "read_later" queue via function call








Random:
- Agent: on return function, validate schema
- Function: use openai decorators

- summarize code: add instruction to use symbol identifiers as tags

- add ask_for_permission callback to Function
- add with minichain.default_logging(logging_function) context manager


# Roadmap


## WebGPT
- add read_later queue


## Programmer
- bash function
- python function
- text_editor
    - loop:
        - initial code base: cwd, tree
        - show_symbols(dir/file) function: summary
        - lookup_symbol(symbol) function: full code
        - edit
    [x] code to symbols
    [ ] SymbolMemory
        [ ] function to view symbol
        [ ] function to edit a symbol,  update line numbers after a symbol has been edited
    [ ] replace in symbol
        - also updates all code lines of the SymbolMemory
    
## Refactor: function decorators


## Planning module
- functions:
    - task board
    - return: {all good / message to refocus}
- planner is called every n steps
- output of the planner appears as a function message in the chat


## UI
- simple web ui that renders all messages
- integrate into vscode

