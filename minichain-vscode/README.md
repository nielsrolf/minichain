# minichain-vscode
[![Demo video](https://img.youtube.com/vi/wxj7qjC8Xb4/0.jpg)](https://www.youtube.com/watch?v=wxj7qjC8Xb4)


Usage: `Cmd+shift P: Open Minichain`.

## Features
Minichain-vscode lets you run a GPT powered programmer inside your project. You can chat with it, and it can run commands, edit files, browse the web (if webgpt is selected) and much more.

## How it works
- commands are run in a docker container with access to the internet, but with POST requests blocked and only the current project mounted
- you can select between a few different modes:
    - yopilot: GPT agent with bash and file edit tools
    - webgpt: GPT agent with google search and a text based browser
    - planner: a GPT project manager that can assign tasks to yopilot and webgpt

# Install
The VSCode extension requires you to have a locally running backend - either started via [docker](#web-ui) or via [python](#python-package) - on `http://localhost:8745`.

You can install the VSCode extension by downloading the `.vsix` file from [releases](https://github.com/nielsrolf/minichain/releases).

To start the extension, you can open Visual Studio Code, go to the Extensions view (Ctrl+Shift+X), and click on the ... (More Actions) button at the top of the view and select Install from VSIX.... Navigate to the minichain-vscode/ directory, select the .vsix file, and click Install. After the installation, you should be able to use the "Open Minichain" command.

## Development

### Installing in development mode
In VSCode, click `cmd` + `shift` + `P`, select: 'Developer: install extension from location', then select `minichain-vscode`. Then reload the window.

### Installing via vsce
Install vsce if you don't have it already:
```
cd minichain-vscode
npm install -g vsce
```

Create the VSCode extension .vsix file:
```
vsce package
```
