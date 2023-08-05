import os
import re

from pydantic import BaseModel, Field

from minichain.agent import Agent, Done, Function, SystemMessage, tool
from minichain.tools.recursive_summarizer import long_document_qa, text_scan
from minichain.utils.generate_docs import get_symbols, summarize_python_file


class RelevantSection(BaseModel):
    start: int = Field(
        ...,
        description="The start line of this section (line numbers are provided in the beginning of each line).",
    )
    end: int = Field(..., description="The end line of this section.")


def get_initial_summary(
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
    available_files = []
    root_dir = root_dir or root_dir
    for root, dirs, filenames in os.walk(root_dir):
        for _filename in filenames:
            filename = os.path.join(root, _filename)
            for extension in extensions:
                if not any(
                    [ignore_file in filename for ignore_file in ignore_files]
                ) and filename.endswith(extension):
                    available_files.append(filename)
    try:
        with open("README.md") as f:
            summary = "\n".join(f.readlines()[:5]) + "...\n"
    except:
        summary = ""
    summary += "Files:\n" + "\n".join(available_files)
    return summary
    

async def get_long_summary(
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
        #     "\n".join(summary.split("\n")[section["start"] : section["end"]])
        #     for section in sections
        # )
        summary = await long_document_qa(
            text=summary,
            question="Summarize the following codebase in order to brief a coworker on this project. Be very concise, and cite important info such as types, function names, and variable names of important code.",
        )
    return summary



@tool()
async def get_file_summary(path: str = Field(..., description="The path to the file.")):
    """Summarize a file."""
    if path.endswith(".py"):
        summary = summarize_python_file(path)
    else:
        print("Summary:", path)
        with open(path, "r") as f:
            text = f.read()
        summary = await long_document_qa(
            text=text,
            question="Summarize the following file in order to brief a coworker on this project. Be very concise, and cite important info such as types, function names, and variable names of important sections. When referencing files, always use the path (rather than the filename).",
        )
    return f"# {path}\n{summary}\n\n"



@tool()
async def scan_file_for_info(
    path: str = Field(..., description="The path to the file."),
    question: str = Field(..., description="The question to ask.")
):
    """Search a file for specific information"""
    if path.endswith(".py"):
        summary = summarize_python_file(path)
    else:
        print("Summary:", path)
        with open(path, "r") as f:
            text = f.read()
        summary = await long_document_qa(
            text=text,
            question=question,
        )
    return f"# {path}\n{summary}\n\n"


@tool()
async def view(
    path: str = Field(..., description="The path to the file."),
    start: int = Field(..., description="The start line."),
    end: int = Field(..., description="The end line."),
    with_line_numbers: bool = Field(
        True, description="Whether to include line numbers in the output."
    ),
):
    """View a section of a file, specified by line range."""
    if start < 0:
        start = 0
    with open(path, "r") as f:
        lines = f.readlines()
        # add line numbers
        if with_line_numbers:
            lines = [f"{i+1} {line}" for i, line in enumerate(lines)]
        response = f"{path} {start}-{end}:\n" + "".join(lines[start:end])
    return response


@tool()
async def edit(
    path: str = Field(..., description="The path to the file."),
    start: int = Field(..., description="The start line."),
    end: int = Field(..., description="The end line."),
    code: str = Field(..., description="The code to replace the lines with."),
):
    """Edit a section of a file, specified by line range."""
    code = remove_line_numbers(code)
    with open(path, "r") as f:
        lines = f.readlines()
        lines[start:end] = code.split("\n")
    with open(path, "w") as f:
        f.write("\n".join(lines))
    updated_in_context = view(
        path=path, start=start - 4, end=start + len(code.split("\n")) + 4, with_line_numbers=True
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
async def replace_symbol(
    path: str = Field(..., description="The path to the file"),
    symbol: str = Field(
        ...,
        description="Either {function_name}, {class_name} or {class_name}.{method_name}. Works for python only.",
    ),
    code: str = Field(..., description="The new code to replace the symbol with."),
    is_new: bool = Field(False, description="Whether a new symbol should be created."),
):
    """Replace a symbol (function/class/method) in a file."""
    symbol_id = symbol
    code = remove_line_numbers(code)
    all_symbols = get_symbols(path)
    for symbol in all_symbols:
        if symbol["id"] == symbol_id:
            with open(symbol["path"], "r") as f:
                lines = f.readlines()
                lines[symbol["start"] : symbol["end"]] = code.split("\n")
            with open(symbol["path"], "w") as f:
                f.write("\n".join(lines))
            updated_in_context = view(
                path=symbol["path"],
                start=symbol["start"] - 4,
                end=symbol["start"] + len(code.split("\n")) + 4,
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
                    start = symbol["end"]
                    break
        else:
            with open(symbol["path"], "r") as f:
                lines = f.readlines()
            start = len(lines)
        end = start + len(code.split("\n"))
        return edit(path=symbol["path"], start=start, end=end, code=code)
    return "Symbol not found. Did you mean to create a new symbol?"


@tool()
async def view_symbol(
    path: str = Field(..., description="The path to the file"),
    symbol: str = Field(
        ...,
        description="Either {function_name}, {class_name} or {class_name}.{method_name}. Works for python only.",
    ),
):
    """Show the full implementation of a symbol (function/class/method) in a file."""
    if not os.path.exists(path):
        # create the file
        with open(path, "w") as f:
            f.write("")
    symbol_id = symbol
    all_symbols = get_symbols(path)
    for symbol in all_symbols:
        all_symbols += symbol.get("methods", [])
    for symbol in all_symbols:
        if symbol["id"] == symbol_id:
            return view(
                path=symbol["path"],
                start=symbol["start"],
                end=symbol["end"],
                with_line_numbers=True,
            )

    for symbol in all_symbols:
        if symbol['id'] == symbol_id:
            return view(
                path=symbol['path'],
                start=symbol['start'],
                end=symbol['end'],
                with_line_numbers=True,
            )
    return "Symbol not found. Available symbols:\n" + "\n".join([symbol['id'] for symbol in all_symbols])


async def test_codebase():
    print(get_initial_summary())
    # out = replace_symbol(path="./minichain/tools/bla.py", symbol="foo", code="test\n", is_new=False)
    print(view_symbol(path="./minichain/agent.py", symbol="Agent.as_function"))
    print(view_symbol(path="./minichain/agent.py", symbol="Function.openapi_json"))
    print(view_symbol(path="./minichain/agent.py", symbol="doesntexist"))


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_codebase())    