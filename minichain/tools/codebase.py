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


def get_inital_summary(
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
    file_summaries = {}
    root_dir = root_dir or root_dir
    for root, dirs, filenames in os.walk(root_dir):
        for _filename in filenames:
            filename = os.path.join(root, _filename)
            for extension in extensions:
                if not any(
                    [ignore_file in filename for ignore_file in ignore_files]
                ) and filename.endswith(extension):
                    file_summaries[filename] = get_file_summary(path=filename)
    # Remove irrelevant files
    summary = file_summaries.pop("README.md", "") + "\n".join(file_summaries.values())
    if len(summary.split(" ")) > 400:
        # sections = text_scan(
        #     summary,
        #     RelevantSection,
        #     "The following is a summary a project's codebase. Your task is to find all sections that seem important to know for a programmer tasked to implement new features or answer questions about the project. The programmer can read specific section in detail, so this summary should mainly give an overview about where to find what. When you are done, call the return function - without an additional summary.",
        # )
        # summary = "\n".join(
        #     "\n".join(summary.split("\n")[section["start_line"] : section["end_line"]])
        #     for section in sections
        # )
        summary = long_document_qa(
            text=summary,
            question="Summarize the following codebase in order to brief a coworker on this project. Be very concise, and cite important info such as types, function names, and variable names of important code.",
        )
    return summary



@tool()
def get_file_summary(path: str = Field(..., description="The path to the file.")):
    """Summarize a file."""
    if path.endswith(".py"):
        summary = summarize_python_file(path)
    else:
        print("Summary:", path)
        with open(path, "r") as f:
            text = f.read()
        summary = long_document_qa(
            text=text,
            question="Summarize the following file in order to brief a coworker on this project. Be very concise, and cite important info such as types, function names, and variable names of important sections. When referencing files, always use the path (rather than the filename).",
        )
    return f"# {path}\n{summary}\n\n"


@tool()
def view(
    path: str = Field(..., description="The path to the file."),
    start: int = Field(..., description="The start line."),
    end: int = Field(..., description="The end line."),
    with_line_numbers: bool = Field(
        True, description="Whether to include line numbers in the output."
    ),
):
    with open(path, "r") as f:
        lines = f.readlines()
        # add line numbers
        if with_line_numbers:
            lines = [f"{i+1} {line}" for i, line in enumerate(lines)]
        return "\n".join(lines[start:end])


@tool()
def edit(
    path: str = Field(..., description="The path to the file."),
    start: int = Field(..., description="The start line."),
    end: int = Field(..., description="The end line."),
    code: str = Field(..., description="The code to replace the lines with."),
):
    code = remove_line_numbers(code)
    with open(path, "r") as f:
        lines = f.readlines()
        lines[start:end] = code.split("\n")
    with open(path, "w") as f:
        f.write("\n".join(lines))
    updated_in_context = view(
        path, start - 4, start + len(code.split("\n")) + 4, with_line_numbers=True
    )
    return truncate_updated(updated_in_context)


def truncate_updated(updated_in_context):
    if len(updated_in_context.split("\n")) > 20:
        # keep firstand last 9 lines with "..." in between
        updated_in_context = (
            updated_in_context.split("\n")[:9]
            + ["..."]
            + updated_in_context.split("\n")[-9:]
        )
        updated_in_context = "\n".join(updated_in_context)
    return updated_in_context


def remove_line_numbers(code):
    # remove line numbers if present using regex
    code = re.sub(r"^\d+ ", "", code, flags=re.MULTILINE)
    return code


@tool()
def replace_symbol(
    path: str = Field(..., description="The path to the file."),
    symbol_id: str = Field(
        ...,
        description="Either {function_name}, {class_name} or {class_name}.{method_name}",
    ),
    code: str = Field(..., description="The new code to replace the symbol with."),
    is_new: bool = Field(False, description="Whether a new symbol should be created."),
):
    code = remove_line_numbers(code)
    all_symbols = get_symbols(path)
    for symbol in all_symbols:
        if symbol["id"] == symbol_id:
            with open(symbol["path"], "r") as f:
                lines = f.readlines()
                lines[symbol["start_line"] : symbol["end_line"]] = code.split("\n")
            with open(symbol["path"], "w") as f:
                f.write("\n".join(lines))
            updated_in_context = view(
                symbol["path"],
                symbol["start_line"] - 4,
                symbol["start_line"] + len(code.split("\n")) + 4,
                with_line_numbers=True,
            )
            return truncate_updated(updated_in_context)
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
        return edit(symbol["path"], start_line, end_line, code)
    return "Symbol not found. Did you mean to create a new symbol?"


@tool()
def show_symbol(
    path: str = Field(..., description="The path to the file."),
    symbol_id: str = Field(
        ...,
        description="Either {function_name}, {class_name} or {class_name}.{method_name}",
    ),
):
    all_symbols = get_symbols(path)
    for symbol in all_symbols:
        if symbol.id == symbol_id:
            return view(
                symbol.path,
                symbol.start_line,
                symbol.end_line,
                with_line_numbers=True,
            )


if __name__ == "__main__":
    print(get_inital_summary())
    breakpoint()
