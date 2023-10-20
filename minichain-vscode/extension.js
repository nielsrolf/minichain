const vscode = require('vscode');
const fs = require('fs');
const path = require('path');


async function assureToken() {
    // Ensure the extension is being used within a workspace
    if (!vscode.workspace.workspaceFolders) {
        console.error("This extension must be used within a workspace.");
        return;
    }

    const workspaceFolder = vscode.workspace.workspaceFolders[0].uri;
    const config = vscode.workspace.getConfiguration('minichain', workspaceFolder);
    const token = config.get('jwt_secret');

    if (!token || token === '') {
        // Set a new random token
        const newToken = Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
        
        try {
            // Update with Workspace scope to specifically target .vscode/settings.json
            await config.update('jwt_secret', newToken, vscode.ConfigurationTarget.Workspace);
            return newToken;
        } catch (error) {
            console.error("Error updating the configuration:", error);
            throw error;
        }
    } else {
		await config.update('jwt_secret', token, vscode.ConfigurationTarget.Workspace);
	}
    return token;
}


function activate(context) {
    let disposable = vscode.commands.registerCommand('extension.openMinichain', function () {
		assureToken().then(token => {
			console.log("open minichain", token);
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
					retainContextWhenHidden: true,
				}
			);
			panel.webview.postMessage({ token: token, cwd: vscode.workspace.workspaceFolders[0].uri.fsPath });
			const htmlContent = getWebviewContent(context, panel, token);
			console.log(htmlContent)
			panel.webview.html = htmlContent;
		});
    });
    context.subscriptions.push(disposable);
}

exports.activate = activate;

function deactivate() { }

exports.deactivate = deactivate;


function getWebviewContent(context, panel, token) {
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