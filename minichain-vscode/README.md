I have created a new folder minichain-vscode/ for the extension and added two files: package.json and extension.js.

In package.json, I defined the basic information about the extension, such as its name, version, and publisher. I also specified the activation event for the extension, which is the command extension.openMinichain.

In extension.js, I implemented the command extension.openMinichain. When this command is triggered, it opens a new tab with a web view of the bundled frontend located in minichain-ui/build/index.html.

Please note that you need to have Node.js and npm installed on your machine to run this extension. Also, you might need to move the minichain-ui/build/ directory to the minichain-vscode/ directory or adjust the path in the extension.js file accordingly.

To install the extension, you can navigate to the minichain-vscode/ directory and run npm install. Then, to start the extension, you can open Visual Studio Code, go to the Extensions view (Ctrl+Shift+X), and click on the ... (More Actions) button at the top of the view and select Install from VSIX.... Navigate to the minichain-vscode/ directory, select the .vsix file, and click Install. After the installation, you should be able to use the "Open Minichain" command.