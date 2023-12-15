import os
import re
import difflib
import subprocess

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

default_extensions = [".py", ".js", ".ts", ".css", "README.md", ".csv", ".json", ".xlsm"]


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
        files = new_files[:max_lines]
        if len(new_files) > max_lines:
            files.append("...")
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
    if len(available_files) == 0:
        return "The current directory is empty."
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
        summary = await long_document_qa(
            text=summary,
            question="Summarize the following codebase in order to brief a coworker on this project. Be very concise, and cite important info such as types, function names, and variable names of important code.",
        )
    return summary


@tool()
async def get_file_summary(path: str = Field(..., description="The path to the file.")):
    """Summarize a file."""
    text, error = open_or_search_file(path)
    if error is not None:
        return error
    if os.path.isdir(path):
        return text
    if path.endswith(".py"):
        summary = summarize_python_file(path)
    else:
        if len(text.replace("\n", " ").split(" ")) > 400:
            print("Summary:", path)
            summary = await long_document_qa(
                text=text,
                question="Summarize the following file in order to brief a coworker on this project. Be very concise, and cite important info such as types, function names, and variable names of important sections. When referencing files, always use the path (rather than the filename).",
            )
        else:
            summary = text
            if text.strip() == "":
                summary = f"Empty file: {path}"
    return f"# {path}\n{summary}\n\n"


@tool()
async def scan_file_for_info(
    path: str = Field(..., description="The path to the file."),
    question: str = Field(..., description="The question to ask."),
):
    """Search a file for specific information"""
    print("Summary:", path)
    text, error = open_or_search_file(path)
    if error is not None:
        return error
    summary = await long_document_qa(
        text=text,
        question=question,
    )
    return f"# {path}\n{summary}\n\n"


def open_or_search_file(path):
    # check if the path is a directory
    if os.path.isdir(path):
        files = get_visible_files(path)
        return None, f"Path is a directory. Did you mean one of: {files}"
    if not os.path.exists(path):
        search_name = path.split("/")[-1]
        # find it in subfolders
        matches = []
        for root, dirs, filenames in os.walk("."):
            for filename in filenames:
                if filename == search_name:
                    matches.append(os.path.join(root, filename))
        if len(matches) == 0:
            return None, f"File not found: {path}"
        elif len(matches) > 1:
            matches = "\n".join(matches)
            return None, f"File not found: {path}. Did you mean one of: {matches}"
        else:
            return None, f"File not found: {path}. Did you mean: {matches[0]}"
    else:
        try:
            with open(path, "r") as f:
                content = f.read()
            return content, None
        except Exception as e:
            return None, f"Error opening file: {e} - use this command only for text / code files, and use pandas or other libraries to interact with other file types."

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
    content, error = open_or_search_file(path)
    if error is not None:
        return error
    lines = content.split("\n")
    with open(path, "r") as f:
        lines = f.readlines()
        # add line numbers
        if with_line_numbers:
            lines = [f"{i+1} {line}" for i, line in enumerate(lines)]
        response = f"{path} {start}-{end}:\n" + "".join(lines[start-1:end])
    return response


def extract_diff_content(line):
    """
    Extract the part of the diff line without the line number.
    For example, for line "-bla.py:3:0: C0116: Missing function or method docstring (missing-function-docstring)",
    it will return "-bla.py::0: C0116: Missing function or method docstring (missing-function-docstring)"
    """
    return re.sub(r'(?<=:)\d+(?=:)', '', line)


def filtered_diff(before, after):
    """
    Generate a diff and filter out lines that only differ by their line number.
    """
    diff = list(difflib.unified_diff(before.splitlines(), after.splitlines()))
    filtered = []
    skip_next = False
    
    for i in range(len(diff)):
        if skip_next:
            skip_next = False
            continue

        if not diff[i].startswith('-') and not diff[i].startswith('+') or diff[i].startswith('---') or diff[i].startswith('+++'):
            continue

        if i < len(diff) - 1 and (diff[i].startswith('-') and diff[i+1].startswith('+')) and \
           extract_diff_content(diff[i][1:]) == extract_diff_content(diff[i+1][1:]):
            skip_next = True
            continue
        filtered.append(diff[i])

    return filtered


@tool()
async def edit(
    path: str = Field(..., description="The path to the file."),
    start: int = Field(..., description="The start line."),
    end: int = Field(..., description="The end line. If end = start, you insert without replacing. To replace a line, set end = start + 1. Use end = -1 to replace until the end of the file."),
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
    
    # Check if the file is a python file
    if path.endswith('.py'):
        # Run pylint on the file before making any changes
        pylint_before = subprocess.run(['pylint', "--score=no", path], capture_output=True, text=True).stdout

    code = remove_line_numbers(code)
    # add indention
    code = "\n".join([indent + line for line in code.split("\n")])
    with open(path, "r") as f:
        lines = f.read().split("\n")
        
    if end < 0:
        end = len(lines) + 2 + end
    
    if end < len(lines) and lines[end - 1].strip() == code.split("\n")[-1].strip():
        end += 1
    
    lines[start - 1 : end - 1] = code.split("\n")
    with open(path, "w") as f:
        f.write("\n".join(lines))
    updated_in_context = await view(
        path=path,
        start=start - 4,
        end=start + len(code.split("\n")) + 4,
        with_line_numbers=True,
    )
    if path.endswith('.py'):
        pylint_after = subprocess.run(['pylint', "--disable=missing-docstring,line-too-long,unused-import,missing-final-newline,bare-except,invalid-name,import-error", "--score=no", path], capture_output=True, text=True).stdout
        # Return the diff of the pylint outputs before and after the changes
        pylint_diff = filtered_diff(pylint_before, pylint_after)
        pylint_new = [line for line in pylint_diff if line.startswith('+')]
        pylint_new = "\n".join(pylint_new)
        # diff = difflib.unified_diff(pylint_before.splitlines(), pylint_after.splitlines())
        # diff = "\n".join(list(diff))
        if pylint_new == "":
            return 'Edit done successfully.'
        return f'Edit done. {path} now has {len(lines)} number of lines. Here are some of pylint hints that appeared since the edit:\n' + pylint_new + "\nYou don't have to fix every linting issue, but check for important ones."
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
    # print(await view_symbol(path="./minichain/agent.py", symbol="Agent.as_function"))
    # print(
    #     await view_symbol(path="./minichain/agent.py", symbol="Function.openapi_json")
    # )
    # print(await view_symbol(path="./minichain/agent.py", symbol="doesntexist"))
    out = await edit(path="./bla.py", start=1, end=1, code="hello(\n", indent="")
    # breakpoint()
    print(out)


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_codebase())
