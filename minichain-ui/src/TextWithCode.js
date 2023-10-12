import React, { useState, useEffect } from 'react';
import CodeBlock from './CodeBlock';
import ReactMarkdown from 'react-markdown';

const TextWithCode = ({ text, run }) => {
  const [textParts, setTextParts] = useState([]);

  useEffect(() => {
    // Regex to match markdown code blocks. Matches everything between ```
    const codeBlockRegex = /```([^`]+)```/g;

    // Split the text into parts: non-code and code. Each part is an object { text, isCode }
    let match;
    let lastIndex = 0;
    const newParts = [];
    while ((match = codeBlockRegex.exec(text)) !== null) {
      if (match.index !== lastIndex) {
        newParts.push({ text: text.slice(lastIndex, match.index), isCode: false });
      }
      newParts.push({ text: match[1], isCode: true });
      lastIndex = match.index + match[0].length;
    }
    if (lastIndex !== text.length) {
      newParts.push({ text: text.slice(lastIndex), isCode: false });
    }

    setTextParts(newParts);
  }, [text]);


  return (
    <div>
      {textParts.map((part, index) => part.isCode
        ? <CodeBlock key={index} code={part.text} run={run}/>
        : <ReactMarkdown key={index}>{part.text.replace(/\n/g, '  \n')}</ReactMarkdown>)}
        {/* // : <ReactMarkdown key={index}>{handleNewlines(part.text)}</ReactMarkdown>)} */}

    </div>
  );
};

export default TextWithCode;
