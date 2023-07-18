from minichain.agent import Agent, SystemMessage
from minichain.memory import SemanticParagraphMemory
# from minichain.tools.code_interpreter import code_interpreter
from minichain.tools.bash import BashSession
# from minichain.tools.codebase import Codebase
from minichain.agents.webgpt import WebGPT, Query



memory = SemanticParagraphMemory()



class Brogrammer(Agent):
    def __init__(self, silent=False, function_stream=lambda i: print(i), **kwargs):
        # codebase = Codebase()
        super().__init__(
            functions=[
                WebGPT(silent=silent).as_function("webgpt", "Research the web in order to answer a question.", Query),
                BashSession(stream=function_stream),
                # code_interpreter,
                # codebase.get_context_about_project, # Should be called in the first step and provide general context about the codebase
                # codebase.qa, # Can be asked in the second step to find the right file
                # codebase.find_symbol, # Can be asked in the next step to get the type description etc of a symbol
                # codebase.replace_symbol, # Edit the codebase - full symbol replacement avoids errors due to wrong start and end positions
                # codebase.edit_lines, # Edit the codebase - line replacement if the section is not part of a symbol or the symbol is too large
            ],
            system_message=SystemMessage(
                # "You are an expert programmer. You can do a wide range of tasks, such as implementing features, debugging and refactoring code, write docs, etc. using the tools available to you. If you need access to up-to-date docs, you can use webgpt - your colleague who researches questions on the web for you. When you implement something, write and run tests to make sure it works. "
                "You are an expert programmer. You can do a wide range of tasks, such as implementing features, debugging and refactoring code, write docs, etc. using bash commands. If you need access to up-to-date docs, you can use webgpt."
            ),
            prompt_template="{query}".format,
            silent=silent,
        )
        # self.codebase = codebase
    

if __name__ == "__main__":
    # webgpt = WebGPT()
    model = Brogrammer(silent=False)
    
    # Using elementary.audio, can you implement a new React component called SyncedAudioStemPlayer that plays a list of stems in a synced loop? The stems are specified by a public URL and need to be loaded into the virtual file system first
    # Can you show me how to use this component in an example?

    while query := input("# User: \n"):
        response = model.run(query=query, keep_session=True)
        print("# Assistant:\n", response)