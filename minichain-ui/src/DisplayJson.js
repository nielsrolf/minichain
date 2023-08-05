import React, { useState } from 'react';




const DisplayJson = ({ data }) => {
  const [isFolded, setIsFolded] = useState({});

  const toggleFold = key => {
    setIsFolded({ ...isFolded, [key]: !isFolded[key] });
  };

  const renderData = (data, parentKey = '') => {
    if ( data === null) {
      return "";
    }

    if (typeof data === 'string') {
        console.log({ parentKey, data })
        try {
            data = JSON.parse(data);
        } catch (e) {
            // if it starts with http, render as a link
            if (data.startsWith("http")) {
                return (
                    <a href={data} target="_blank" rel="noopener noreferrer">
                        {data}
                    </a>
                )
            }  else {
                return data;
            }
        }
    }
    return Object.entries(data).map(([key, value]) => {
      const newKey = `${parentKey}.${key}`;
    //   if (typeof value === 'object' && value !== null) {
        return (
          <div key={newKey} style={{ marginLeft: '20px' }}>
            <b style={{ cursor: 'pointer' }} onClick={() => toggleFold(newKey)}>
              {key + " "}
            </b>
            {!isFolded[newKey] && renderData(value, newKey)}
          </div>
        );
    //   } else {
    //     console.log("string", { key, value })
    //     return (
    //       <div key={newKey} style={{ marginLeft: '20px' }}>
    //         <b>{key}</b>: {value.toString()}
    //       </div>
    //     );
    //   }
    });
  };

  return <div>{renderData(data)}</div>;
};

export default DisplayJson;
