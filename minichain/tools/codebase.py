import os
import re

from pydantic import BaseModel, Field

from minichain.agent import Agent, Done, Function, SystemMessage, tool
from minichain.tools.recursive_summarizer import long_document_qa, text_scan
from minichain.utils.generate_docs import get_symbols, summarize_python_file


class RelevantSection(BaseModel):
    start_line: int = Field(
        ...,
        description="The start line of this section (line numbers are provided in the beginning of each line).",
    )
    end_line: int = Field(..., description="The end line of this section.")


class Codebase:
    def __init__(
        self,
        root_dir=".",
        extensions=[".py", ".js", ".ts", "README.md"],
        ignore_files=[
            ".git/",
            ".vscode/",
            "__pycache__/",
            "node_modules/",
            "dist/",
            "build/",
            "venv/",
            "env/",
        ],
    ):
        self.root_dir = root_dir
        self.extensions = extensions
        self.ignore_files = ignore_files

    def get_inital_summary(self, root_dir=None):
        file_summaries = {}
        root_dir = root_dir or self.root_dir
        for root, dirs, filenames in os.walk(root_dir):
            for _filename in filenames:
                filename = os.path.join(root, _filename)
                for extension in self.extensions:
                    if not any(
                        [ignore_file in filename for ignore_file in self.ignore_files]
                    ) and filename.endswith(extension):
                        file_summaries[filename] = self.get_file_summary(filename)
        # Remove irrelevant files
        summary = file_summaries.pop("README.md", "") + "\n".join(
            file_summaries.values()
        )
        if len(summary.split(" ")) > 400:
            sections = text_scan(
                summary,
                RelevantSection,
                "The following is a summary a project's codebase. Your task is to find all sections that seem important to know for a programmer tasked to implement new features or answer questions about the project. The programmer can read specific section in detail, so this summary should mainly give an overview about where to find what.",
            )
            summary = "\n".join(
                "\n".join(
                    summary.split("\n")[section["start_line"] : section["end_line"]]
                )
                for section in sections
            )

    @tool()
    def get_file_summary(self, path):
        if path.endswith(".py"):
            summary = summarize_python_file(path)
        else:
            print("Summary:", path)
            with open(path, "r") as f:
                text = f.read()
            summary = long_document_qa(
                text=text,
                question="Summarize the following file in order to brief a coworker on this project. Be very concise, and cite important info such as types, function names, and variable names of important sections.",
            )
        return f"# {path}\n{summary}\n\n"

    @tool()
    def view(self, path, start, end, with_line_numbers=True):
        with open(path, "r") as f:
            lines = f.readlines()
            # add line numbers
            if with_line_numbers:
                lines = [f"{i+1} {line}" for i, line in enumerate(lines)]
            return "\n".join(lines[start:end])

    @tool()
    def edit(self, path, start, end, code):
        code = self.remove_line_numbers(code)
        with open(path, "r") as f:
            lines = f.readlines()
            lines[start:end] = code.split("\n")
        with open(path, "w") as f:
            f.write("\n".join(lines))
        updated_in_context = self.view(
            path, start - 4, start + len(code.split("\n")) + 4, with_line_numbers=True
        )
        return self.truncate_updated(updated_in_context)

    def truncate_updated(self, updated_in_context):
        if len(updated_in_context.split("\n")) > 20:
            # keep firstand last 9 lines with "..." in between
            updated_in_context = (
                updated_in_context.split("\n")[:9]
                + ["..."]
                + updated_in_context.split("\n")[-9:]
            )
            updated_in_context = "\n".join(updated_in_context)
        return updated_in_context

    def remove_line_numbers(self, code):
        # remove line numbers if present using regex
        code = re.sub(r"^\d+ ", "", code, flags=re.MULTILINE)
        return code

    @tool()
    def replace_symbol(self, file, symbol_id, code, is_new=False):
        code = self.remove_line_numbers(code)
        all_symbols = get_symbols(file)
        for symbol in all_symbols:
            if symbol["id"] == symbol_id:
                with open(symbol["path"], "r") as f:
                    lines = f.readlines()
                    lines[symbol["start_line"] : symbol["end_line"]] = code.split("\n")
                with open(symbol["path"], "w") as f:
                    f.write("\n".join(lines))
                updated_in_context = self.view(
                    symbol["path"],
                    symbol["start_line"] - 4,
                    symbol["start_line"] + len(code.split("\n")) + 4,
                    with_line_numbers=True,
                )
                return self.truncate_updated(updated_in_context)
        if is_new:
            # Find the last line of the file or class and insert the new symbol there
            # Check if it's a class method
            if "." in symbol_id:
                class_name, method_name = symbol_id.split(".")
                for symbol in all_symbols:
                    if symbol["id"] == class_name:
                        start_line = symbol["end_line"]
                        break
            else:
                with open(symbol["path"], "r") as f:
                    lines = f.readlines()
                start_line = len(lines)
            end_line = start_line + len(code.split("\n"))
            return self.edit(symbol["path"], start_line, end_line, code)
        return "Symbol not found. Did you mean to create a new symbol?"

    @tool()
    def show_symbol(self, file, symbol_id):
        all_symbols = get_symbols(file)
        for symbol in all_symbols:
            if symbol.id == symbol_id:
                return self.view(
                    symbol.path,
                    symbol.start_line,
                    symbol.end_line,
                    with_line_numbers=True,
                )


if __name__ == "__main__":
    codebase = Codebase(root_dir=".")
    print(codebase.get_inital_summary())
    breakpoint()
