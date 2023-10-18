"""
TODO
- docstring parsing is broken
- save line range to symbol
"""


import os
from pprint import pprint

import click


def parse_function(code, file, id_prefix=""):
    lines = code.split("\n")
    end_line = 0
    try:
        while not (lines[end_line].startswith("def ") or lines[end_line].startswith("async def ")):
            end_line += 1
    except IndexError:
        return None, len(lines)
    line = lines[end_line]
    try:
        function_name = line.split("def ")[1].split("(")[0]
    except:
        # breakpoint()
        pass
    function_signature = ""
    for potential_signature_end in lines[end_line:]:
        end_line += 1
        function_signature += potential_signature_end + "\n"
        if potential_signature_end.split("#")[0].strip().endswith(":"):
            break
    docstring = ""
    if lines[end_line].strip().startswith('"""'):
        for potential_docstring_end in lines[end_line:]:
            end_line += 1
            docstring += potential_docstring_end
            if potential_docstring_end.strip().endswith('"""'):
                break
    code = ""
    for line in lines[end_line:]:
        if line.startswith(" ") or line.startswith("\t") or line == "":
            code += line + "\n"
            end_line += 1
        else:
            break
    i = end_line
    return {
        "name": function_name,
        "signature": function_signature,
        "docstring": docstring,
        "code": code,
        "path": file,
        "start": 0,
        "end": i - 1,
        "id": f"{id_prefix}{function_name}",
    }, i


def parse_functions(code, file, id_prefix=""):
    functions = []
    while code:
        function, i = parse_function(code, file, id_prefix=id_prefix)
        if function is not None:
            functions.append(function)
        code = "\n".join(code.split("\n")[i:])
    return functions


def get_symbols(file):
    symbols = []
    with open(file) as f:
        content = f.read()
        lines = content.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        # print(line)
        if line.startswith("def ") or line.startswith("async def "):
            function, j = parse_function("\n".join(lines[i:]), file)
            function["start"] += i
            function["end"] += i
            i += j
            symbols += [function]
        elif line.startswith("class "):
            class_start_line = i
            class_name = line.split("class ")[1].split("(")[0]
            class_signature = ""
            end_line = i
            for potential_signature_end in lines[i:]:
                end_line += 1
                class_signature += potential_signature_end
                if potential_signature_end.split("#")[0].strip().endswith(":"):
                    break
            docstring = ""
            if lines[end_line].strip().startswith('"""'):
                end_line += 1
                for potential_docstring_end in lines[end_line:]:
                    end_line += 1
                    docstring += potential_docstring_end
                    if potential_docstring_end.strip().endswith('"""'):
                        docstring = docstring.strip('"""')
                        break
            code_start_line = end_line
            code = ""
            for line in lines[end_line:]:
                if line.startswith(" ") or line.startswith("\t") or line == "":
                    code += line + "\n"
                    end_line += 1
                else:
                    break
            i = end_line
            # parse the methods from the code

            # get the indention of the first line
            indention_str = ""
            for char in code.split("\n")[0]:
                if char == " " or char == "\t":
                    indention_str += char
                else:
                    break
            # remove the indention from the code
            unindented_code = [
                line.replace(indention_str, "", 1) for line in code.split("\n")
            ]
            # if dataclass etc, parse the fields. we know it's a dataclass if the first code line is not a def
            fields = ""
            while len(unindented_code) > 0 and not unindented_code[0].startswith(
                "def "
            ):
                fields += unindented_code[0] + "\n"
                unindented_code = unindented_code[1:]
            fields = fields.strip()

            if len(unindented_code) == 0:
                methods = []
            else:
                # methods_code = "\n".join([i for i in unindented_code if not i == "" and not i.strip().startswith("#") and not i.strip().startswith("@")])
                methods_code = "\n".join(unindented_code)
                if methods_code.strip() == "":
                    methods = []
                else:
                    methods = parse_functions(
                        methods_code, file, id_prefix=f"{class_name.split(':')[0]}."
                    )
                for m in methods:
                    m["start"] += code_start_line
                    m["end"] += code_start_line
                    code_start_line = m["end"] + 1
                methods[-1]["end"] -= 1
            symbols.append(
                {
                    "name": class_name,
                    "signature": class_signature,
                    "docstring": docstring,
                    "code": code,
                    "path": file,
                    "methods": methods,
                    "fields": fields,
                    "start": class_start_line,
                    "end": end_line - 1,
                    "id": f"{class_name.split(':')[0]}",
                }
            )
        else:
            i += 1
    return symbols


def generate_docs(src):
    # Step 1: Get all files
    files = []
    for root, dirs, filenames in os.walk(src):
        for filename in filenames:
            if filename.endswith(".py"):
                files.append(os.path.join(root, filename))
    # Step 2: Get all functions, classes, and methods
    symbols = []
    for file in files:
        symbols += get_symbols(file)
    return symbols


def symbol_as_markdown(symbol, prefix=""):
    response = ""

    def print(*args, **kwargs):
        nonlocal response
        response += " ".join([str(i) for i in args]) + "\n"

    print(f"{prefix}{symbol['signature']}Lines: {symbol['start']}-{symbol['end']}")
    if symbol["docstring"]:
        print(f"{prefix}{symbol['docstring']}")
    if symbol.get("fields"):
        fields = symbol["fields"].split("\n")
        fields = "\n".join([f"{prefix}    {i}" for i in fields])
        print(fields)
    if symbol.get("methods"):
        for method in symbol["methods"]:
            print(symbol_as_markdown(method, prefix=f"    "))
    print()
    return response


def summarize_python_file(path):
    symbols = get_symbols(path)
    symbols = "\n\n".join([symbol_as_markdown(i) for i in symbols])
    return f"The file {path} contains the following symbols:\n\n{symbols}"


@click.command()
@click.argument("src")
def main(src):
    print(src)
    symbols = generate_docs(src)
    symbols_by_file = {
        file: [i for i in symbols if i["path"] == file]
        for file in set([i["path"] for i in symbols])
    }
    for file, symbols in symbols_by_file.items():
        print(f"## {file}")
        for i in symbols:
            print(symbol_as_markdown(i))


if __name__ == "__main__":
    # main()
    print(summarize_python_file("minichain/memory.py"))
