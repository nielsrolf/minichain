import React, { useState, useEffect } from 'react';
import CodeBlock from './CodeBlock';

const TextWithCode = ({ text }) => {
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
        ? <CodeBlock key={index} code={part.text} />
        : <p key={index}>{part.text}</p>)}
    </div>
  );
};

export default TextWithCode;
