import React, { useState } from 'react';
import TextWithCode from './TextWithCode';
import './DisplayJson.css';
import CodeBlock from './CodeBlock';


const MultiMedia = ({ path }) => {
  console.log("multimedia:", {path})
  if (!path) {
    return '';
  }
  const url = path.startsWith("http") ? path : `http://localhost:8745/static/${path}`;
  // get the file type
  const extension = path.split('.').pop();
  if (['png', 'jpg', 'jpeg', 'gif'].includes(extension)) {
    return(
      <div class="media-container">
        {path} <br />
        <img src={url} alt="uploaded file" />
      </div>
    );
  }
  if (['mp4', 'webm'].includes(extension)) {
    return (
      <div class="media-container">
        {path} <br />
        <video controls>
          <source src={url} type={`video/${extension}`} />
        </video>
      </div>
    );
  }
  if (['mp3', 'wav'].includes(extension)) {
    return (
      <div class="media-container">
        {path} <br />  
        <audio controls>
          <source src={url} type={`audio/${extension}`} />
        </audio>
      </div>
    );
  }
  return path;
};


const DisplayJson = ({ data }) => {
  const [isFolded, setIsFolded] = useState({});
  // First: all the special cases
  if (!data) {
    return '';
  }
  // if (data.name === 'python') {
  //   console.log(data);
  //   return <CodeBlock code={data.arguments} />;
  // }
  try {
    if (data.name === 'return' && JSON.parse(data.arguments).content) {
      return;
    }
  } catch (e) {
    // arguments was not a json
  }
  if (typeof data === 'string' && data.startsWith('displaying file:')) {
    const path = data.split('displaying file:')[1].trim();
    return <MultiMedia path={path} />;
  }

  if (data.generated_files) {
    // simply display all files
    return (
      <div>
        {data.generated_files.map((file, index) => (
          <div key={index}>
            <b>{file}</b>
            <MultiMedia path={file} />
          </div>
        ))}
      </div>
    );
  }

  const toggleFold = key => {
    setIsFolded({ ...isFolded, [key]: !isFolded[key] });
  };

  const removeLineNumbers = code => 
    code.split('\n').map(line => line.replace(/^\d+:\s*/, '')).join('\n');

  const renderData = (data, parentKey = '') => {
    if (data === null || data === undefined) {
      return '';
    }

    // all links should be medias
    if (typeof data === 'string' && data.startsWith('http')) {
      return <MultiMedia path={data} />;
    }

    if (typeof data === 'string') {
      try {
        data = JSON.parse(data);
      } catch (e) {
        if (data.startsWith('http')) {
          return (
            <a href={data} target="_blank" rel="noopener noreferrer">
              {data}
            </a>
          );
        } else {
          return <TextWithCode text={data} />;
        }
      }
    }

    if (typeof data === 'number' || typeof data === 'boolean') {
        return data.toString();
    }

    if (Array.isArray(data)) {
      return (
        <div>
          {data.map((item, index) => {
            renderData(item, `${parentKey}.${index}`);
          })}
        </div>
      );
    }
    if (data === null || data === undefined) {
      return '';
    }
    return Object.entries(data).map(([key, value]) => {
      const newKey = `${parentKey}.${key}`;
      if (key === 'code') {
        return (
            <CodeBlock key={newKey} code={removeLineNumbers(value)} />
        );
      }
      return (
        <div key={newKey} style={{ marginLeft: '20px' }}>
          <b style={{ cursor: 'pointer' }} onClick={() => toggleFold(newKey)}>
            {key + ' '}
          </b>
          {!isFolded[newKey] && (
            key === 'code'
              ? <CodeBlock code={removeLineNumbers(value)} />
              : renderData(value, newKey)
          )}
        </div>
      );
    });
  };

  return <div>{renderData(data)}</div>;
};

export default DisplayJson;
