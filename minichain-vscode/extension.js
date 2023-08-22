const vscode = require('vscode');
const fs = require('fs');
const path = require('path');


function activate(context) {


    let disposable = vscode.commands.registerCommand('extension.openMinichain', function () {
        // make an info box for debugging with context.extensionPath
        vscode.window.showInformationMessage(context.extensionPath);
        let panel = vscode.window.createWebviewPanel(
            'minichain',
            'Minichain',
            vscode.ViewColumn.One,
            {
                // Enable scripts in the webview
                enableScripts: true,
                localResourceRoots: [
                    vscode.Uri.file(path.join(context.extensionPath, 'build')),
                ],
            }
        );
        const htmlContent = getWebviewContent(context, panel);
        console.log(htmlContent)
        panel.webview.html = htmlContent;
    });

    context.subscriptions.push(disposable);
}

exports.activate = activate;

function deactivate() { }

exports.deactivate = deactivate;


function getWebviewContent(context, panel) {
	const buildPath = path.join(context.extensionPath, 'build');
	const indexPath = path.join(buildPath, 'index.html');
	let html = fs.readFileSync(indexPath, 'utf8');

	// Get the JS and CSS file names dynamically
	const jsFile = fs.readdirSync(path.join(buildPath, 'static', 'js')).find(file => file.startsWith('main.'));
	const cssFile = fs.readdirSync(path.join(buildPath, 'static', 'css')).find(file => file.startsWith('main.'));

	// Replace the script src and css href with the correct vscode-resource URLs
	html = html.replace(
		/src="\/static\/js\/main\..*\.js"/g,
		`src="${panel.webview.asWebviewUri(vscode.Uri.file(path.join(buildPath, 'static', 'js', jsFile)))}"`
	);
	html = html.replace(
		/href="\/static\/css\/main\..*\.css"/g,
		`href="${panel.webview.asWebviewUri(vscode.Uri.file(path.join(buildPath, 'static', 'css', cssFile)))}"`
	);

	// Inject the vscode API
	const vscodeScript = `
		<script>
		window.vscode = acquireVsCodeApi();
		</script>
	`;
	html = html.replace('</body>', `${vscodeScript}</body>`);

	return html;
}