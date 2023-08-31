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

## Install
Currently the extension can only be installed in dev mode.

## Dev setup
Clone the repo and install the extension in this folder using `Cmd+shift P: Developer: Install extension from location...`.


## Original note from `minichain.agents.programmer.Programmer` who made the extension
I have created a new folder minichain-vscode/ for the extension and added two files: package.json and extension.js.

In package.json, I defined the basic information about the extension, such as its name, version, and publisher. I also specified the activation event for the extension, which is the command extension.openMinichain.

In extension.js, I implemented the command extension.openMinichain. When this command is triggered, it opens a new tab with a web view of the bundled frontend located in minichain-ui/build/index.html.

Please note that you need to have Node.js and npm installed on your machine to run this extension. Also, you might need to move the minichain-ui/build/ directory to the minichain-vscode/ directory or adjust the path in the extension.js file accordingly.

To install the extension, you can navigate to the minichain-vscode/ directory and run npm install. Then, to start the extension, you can open Visual Studio Code, go to the Extensions view (Ctrl+Shift+X), and click on the ... (More Actions) button at the top of the view and select Install from VSIX.... Navigate to the minichain-vscode/ directory, select the .vsix file, and click Install. After the installation, you should be able to use the "Open Minichain" command.