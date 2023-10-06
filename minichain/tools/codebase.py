import os
import re

from pydantic import BaseModel, Field

from minichain.functions import tool
from minichain.tools.recursive_summarizer import long_document_qa
from minichain.utils.generate_docs import get_symbols, summarize_python_file


default_ignore_files = [
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    "venv",
    "env",
    "examples",
    "htmlcov",
]

default_extensions = [".py", ".js", ".ts", ".css", "README.md"]


class RelevantSection(BaseModel):
    start: int = Field(
        ...,
        description="The start line of this section (line numbers are provided in the beginning of each line).",
    )
    end: int = Field(..., description="The end line of this section.")


def get_visible_files(
    root_dir, extensions=default_extensions, ignore_files=default_ignore_files, max_lines=100
):
    def should_ignore(path):
        for ignore in ignore_files:
            if ignore in path:
                return True
        return False

    def list_files(directory, depth=1):
        entries = []
        try:
            for name in os.listdir(directory):
                # check if it's a hidden file
                if name.startswith("."):
                    continue
                path = os.path.join(directory, name)
                rel_path = os.path.relpath(path, root_dir)
                if should_ignore(rel_path):
                    continue
                if os.path.isdir(path) and depth > 0:
                    entries.extend(list_files(path, depth - 1))
                elif os.path.isdir(path):
                    entries.append(rel_path + "/")
                else:
                    if any(rel_path.endswith(ext) for ext in extensions):
                        entries.append(rel_path)
        except PermissionError:
            pass
        return entries

    depth = 0
    files, new_files = [], []
    while (
        len(new_files) <= max_lines and depth < 10
    ):  # Limiting depth to avoid infinite loops
        files = new_files
        new_files = list_files(root_dir, depth)
        depth += 1

    if files == []:
        files = new_files[:max_lines] + ["..."]
    return files


def get_initial_summary(
    root_dir=".",
    extensions=default_extensions,
    ignore_files=default_ignore_files,
    max_lines=40,
):
    available_files = get_visible_files(
        root_dir=root_dir,
        extensions=extensions,
        ignore_files=ignore_files,
        max_lines=max_lines,
    )
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
        ".cache/",
        ".minichain/",
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
    if not os.path.exists(path):
        return f"File not found: {path}"
    if path.endswith(".py"):
        summary = summarize_python_file(path)
    else:
        print("Summary:", path)
        try:
            with open(path, "r") as f:
                text = f.read()
        except Exception as e:
            return f"Could not read file: {e}"
        summary = await long_document_qa(
            text=text,
            question="Summarize the following file in order to brief a coworker on this project. Be very concise, and cite important info such as types, function names, and variable names of important sections. When referencing files, always use the path (rather than the filename).",
        )
    return f"# {path}\n{summary}\n\n"


@tool()
async def scan_file_for_info(
    path: str = Field(..., description="The path to the file."),
    question: str = Field(..., description="The question to ask."),
):
    """Search a file for specific information"""
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
    if start < 1:
        start = 1
    with open(path, "r") as f:
        lines = f.readlines()
        # add line numbers
        if with_line_numbers:
            lines = [f"{i+1} {line}" for i, line in enumerate(lines)]
        response = f"{path} {start}-{end}:\n" + "".join(lines[start-1:end])
    return response


@tool()
async def edit(
    path: str = Field(..., description="The path to the file."),
    start: int = Field(..., description="The start line."),
    end: int = Field(..., description="The end line. If end = start, you insert without replacing. To replace a line, set end = start + 1."),
    indent: str = Field("", description="Prefix of spaces for each line to use as indention. Example: '    '"),
    code: str = Field(
        ...,
        description="The code to replace the lines with.",
    ),
):
    """Edit a section of a file, specified by line range. NEVER edit lines of files before viewing them first!
    Creates the file if it does not exist, then replaces the lines (including start and end line) with the new code.
    Use this method instead of bash touch or echo to create new files.
    Keep the correct indention, especially in python files.
    """
    if not os.path.exists(path):
        # check if the dir exists
        dir_path = os.path.dirname(path)
        try:
            os.makedirs(dir_path, exist_ok=True)
        except:
            # maybe we are trying to write to cwd, in which case this fails for some reason
            pass
        # create the file
        with open(path, "w") as f:
            f.write("")
    code = remove_line_numbers(code)
    # add indention
    code = "\n".join([indent + line for line in code.split("\n")])
    with open(path, "r") as f:
        lines = f.read().split("\n")
        lines[start - 1 : end - 1] = code.split("\n")
    with open(path, "w") as f:
        f.write("\n".join(lines))
    updated_in_context = await view(
        path=path,
        start=start - 4,
        end=start + len(code.split("\n")) + 4,
        with_line_numbers=True,
    )
    return truncate_updated(updated_in_context)


def truncate_updated(updated_in_context):
    if len(updated_in_context.split("\n")) > 20:
        # keep first and last 9 lines with "..." in between
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
    code: str = Field(
        ...,
        description="The new code to replace the symbol with. Can be escaped with `ticks` to avoid formatting code as JSON.",
    ),
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
            updated_in_context = await view(
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
        description="Either {function_name}, {class_name} or {class_name}.{method_name}. Works for python only, use view for other files.",
    ),
):
    """Show the full implementation of a symbol (function/class/method) in a file."""
    if not path.endswith(".py"):
        raise ValueError("Only python files are supported.")
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
            return await view(
                path=symbol["path"],
                start=symbol["start"],
                end=symbol["end"],
                with_line_numbers=True,
            )

    for symbol in all_symbols:
        if symbol["id"] == symbol_id:
            return await view(
                path=symbol["path"],
                start=symbol["start"],
                end=symbol["end"],
                with_line_numbers=True,
            )
    return "Symbol not found. Available symbols:\n" + "\n".join(
        [symbol["id"] for symbol in all_symbols]
    )


async def test_codebase():
    print(get_initial_summary())
    # out = replace_symbol(path="./minichain/tools/bla.py", symbol="foo", code="test\n", is_new=False)
    print(await view_symbol(path="./minichain/agent.py", symbol="Agent.as_function"))
    print(
        await view_symbol(path="./minichain/agent.py", symbol="Function.openapi_json")
    )
    print(await view_symbol(path="./minichain/agent.py", symbol="doesntexist"))


# if __name__ == "__main__":
#     import asyncio

#     asyncio.run(test_codebase())
