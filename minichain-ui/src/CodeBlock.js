import React, { useState } from 'react';

import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { twilight as codeStyle } from 'react-syntax-highlighter/dist/esm/styles/prism';


const languages = [
    'javascript',
    'python',
    'java',
    'c',
    'cpp',
    'csharp',
    'go',
    'kotlin',
    'php',
    'ruby',
    'rust',
    'scala',
    'swift',
    'typescript',
    'dart',
    'elixir',
    'haskell',
    'ocaml',
    'perl',
    'r',
    'sql',
    'bash',
    'py',
    'sh',
    'zsh',
    'json',
    'yaml',
    'html',
    'css',
    'js',
    'jsx',
    'tsx',
    'xml',
    'ts'
]

const CodeBlock = ({ code }) => {
    const [hasCopied, setHasCopied] = useState(false);
    if (typeof code !== 'string') {
        code = code.code;
    }
    if (!code) {
        return '';
    }
    // check if the code starts with a language name
    let language = languages.find(l => code.startsWith(l));
    // if it does, remove the language name from the code
    if (language) {
        code = code.slice(language.length + 1);
    } else {
        // otherwise, default to python
        language = 'python';
    }

    const copyToClipboard = () => {
        navigator.clipboard.writeText(code);
        setHasCopied(true);
        setTimeout(() => setHasCopied(false), 2000); // Reset after 2 seconds
    };

    return (
        <div style={{ position: 'relative', display: 'flex', flexDirection: 'column', alignItems: 'flex-start', backgroundColor: "rgba(0, 0, 0, 0.2)", width: "100%" }}>
            <button
                onClick={copyToClipboard}
                style={{ position: 'absolute', top: 0, right: 0 }}
            >
                {hasCopied ? 'Copied!' : 'Copy'}
            </button>
            <div style={{ width: '100%', overflowX: 'auto' }}>
                <SyntaxHighlighter language={language} style={codeStyle}>
                    {code}
                </SyntaxHighlighter>
            </div>
        </div>
    );
};

export default CodeBlock;