import React, { useState } from 'react';
import Editor from '@monaco-editor/react';


function NewCell({onRun}) {
    const [editorIsOpen, setEditorIsOpen] = useState(false);
    const [editorValue, setEditorValue] = useState('');


    if (!editorIsOpen) {
        return (
            <div className="new-cell">
                <button onClick={() => {
                    setEditorIsOpen(true);
                    // wait a few ms, then scroll to bottom
                    setTimeout(() => {
                        window.scrollTo(0,document.body.scrollHeight);
                    }, 10);
                }}>New Cell</button>
            </div>
        );
    }
    return (
        <div className="new-cell">
            <button onClick={() => setEditorIsOpen(false)}>Close</button>
            <Editor
                height="50vh"
                width="100%"
                defaultLanguage="python"
                defaultValue=""
                theme="vs-dark"
                onChange={(value) => setEditorValue(value)}
            />
            <button onClick={async () => {
                await onRun(editorValue);
                setEditorIsOpen(false);
            }}>
                Save
            </button>
        </div>
    );
}

export default NewCell;