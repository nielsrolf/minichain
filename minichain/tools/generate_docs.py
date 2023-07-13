import click
import os


def generate_docs(src):
    # Use pydoc-markdown to generate markdown files from python files
    pass
              

@click.command()
@click.argument("src")
def main(src):
    generate_docs(src)


if __name__ == "__main__":
    main()
    