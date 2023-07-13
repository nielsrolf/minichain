import click
import os
from pprint import pprint


def parse_functions(code, file):
    lines = code.split("\n")
    line = lines[0]
    function_name = line.split("def ")[1].split("(")[0]
    function_signature = ""
    end_line = 0
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
        if line.startswith(" ") or line.startswith("\t"):
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
        }, i


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
            functions, j = parse_functions("\n".join(lines[i:]), file)
            i += j
            symbols += functions
        elif line.startswith("class "):
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
                if line.startswith(" ") or line.startswith("\t"):
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
            while len(unindented_code) > 0 and not unindented_code[0].startswith("def "):
                fields += unindented_code[0] + "\n"
                unindented_code = unindented_code[1:]
            fields = fields.strip()
            
            if len(unindented_code) == 0:
                methods = []
            else:
                methods, j = parse_functions("\n".join(unindented_code), file)
                i += j
            symbols.append(
                {
                    "name": class_name,
                    "signature": class_signature,
                    "docstring": docstring,
                    "code": code,
                    "path": file,
                    "methods": methods,
                    "fields": fields,
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
    breakpoint()
    # Step 3: Generate docs
    for symbol in symbols:
        pprint(symbol)

              

@click.command()
@click.argument("src")
def main(src):
    generate_docs(src)


if __name__ == "__main__":
    main()
    