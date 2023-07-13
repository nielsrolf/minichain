"""
TODO
- docstring parsing is broken
- save line range to symbol
"""



import click
import os
from pprint import pprint


def parse_function(code, file):
    lines = code.split("\n")
    end_line = 0
    try:
        while not lines[end_line].startswith("def "):
            end_line += 1
    except IndexError:
        return None, len(lines)
    line = lines[end_line]
    try:
        function_name = line.split("def ")[1].split("(")[0]
    except:
        breakpoint()
    function_signature = ""
    for potential_signature_end in lines[end_line:]:
        end_line += 1
        function_signature += potential_signature_end
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
            "end": i,
        }, i


def parse_functions(code, file):
    functions = []
    while code:
        function, i = parse_function(code, file)
        if function is not None:
            functions.append(function)
        code = "\n".join(code.split("\n")[i:])
    return functions

def get_symbols(file):
    print(file)
    symbols = []
    with open(file) as f:
        content = f.read()
        lines = content.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        # print(line)
        if line.startswith("def "):
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
            # parse the methods from the code
            code_start_line = i
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
            while len(unindented_code) > 0 and not unindented_code[0].startswith("def "):
                fields += unindented_code[0] + "\n"
                unindented_code = unindented_code[1:]
            fields = fields.strip()
            
            if len(unindented_code) == 0:
                methods = []
            else:
                # methods_code = "\n".join([i for i in unindented_code if not i == "" and not i.strip().startswith("#") and not i.strip().startswith("@")])
                methods_code =  "\n".join(unindented_code)
                if methods_code.strip() == "":
                    methods = []
                else:
                    methods = parse_functions(methods_code, file)
                for m in methods:
                    m["start"] += code_start_line
                    m["end"] += code_start_line
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
                    "end": end_line,
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
                print(filename)
                files.append(os.path.join(root, filename))
    # Step 2: Get all functions, classes, and methods
    symbols = []
    for file in files:
        symbols += get_symbols(file)
    return symbols


def print_symbol_as_markdown(symbol, prefix=""):
    try:
        print(f"{prefix}{symbol['signature']} {symbol['start']}-{symbol['end']}")
    except:
        breakpoint()
    if symbol["docstring"]:
        print(f"{prefix}  docstring: {symbol['docstring']}")
    if symbol.get("fields"):
        print(symbol["fields"])
    if symbol.get("methods"):
        for method in symbol["methods"]:
            print_symbol_as_markdown(method, prefix=f"    ")
    print()

              

@click.command()
@click.argument("src")
def main(src):
    print(src)
    symbols = generate_docs(src)
    symbols_by_file = {  file: [i for i in symbols if i["path"] == file] 
                        for file in set([i["path"] for i in symbols])}
    for file, symbols in symbols_by_file.items():
        print(f"## {file}")
        for i in symbols:
            print_symbol_as_markdown(i)


if __name__ == "__main__":
    main()
    
