import DisplayJson from './DisplayJson';
import CodeBlock from "./CodeBlock";
import './ChatApp.css';
import { useEffect } from 'react';
import CloseIcon from '@mui/icons-material/Close';
import ThumbUpOutlinedIcon from '@mui/icons-material/ThumbUpOutlined';
import ThumbUpIcon from '@mui/icons-material/ThumbUp';
import ThumbDownIcon from '@mui/icons-material/ThumbDown';
import ThumbDownOutlinedIcon from '@mui/icons-material/ThumbDownOutlined';
import ForkRightIcon from '@mui/icons-material/ForkRight';

const functionsToRenderAsCode = [
    "jupyter",
    "view",
    "edit",
    "view_symbol",
    "replace_symbol",
];

function DisplayData({data}){
    // this renders a single entry of a message that comes from jupyter
    console.log("displaying data:", data);

    useEffect(() => {
        if (data['text/html']) {
            const script = document.createElement("script");
            // extract the script from the html <script type="text/javascript"> 
            const regex = /<script type="text\/javascript">([\s\S]*)<\/script>/;
            const match = data['text/html'].match(regex);
            if (!match) {
                return;
            }
            
            // This is where you remove the require call and use the contents directly
            const modifiedScriptContent = match[1].replace(
                /require\(\["plotly"\], function\(Plotly\) {([\s\S]*)}\);/,
                "$1"
            );
    
            script.innerHTML = modifiedScriptContent;
            document.body.appendChild(script);
        }
    }, [data]);

    if (data['image/png']) {
        return <div className='media-container'><img src={`data:image/png;base64,${data['image/png']}`} alt={`${data['text/plain']}`} /></div>;
    }
    if (data['text/html']) {
        return <div dangerouslySetInnerHTML={{__html: data['text/html']}} />;
    }
    console.log("cannot display data:");
    console.log(data);
}


function formatTimestamp(timestamp) {
    // Return a timestamp in a human readable format, e.g.:
    // - if timestamp is less than 24 hours ago: {duration} ago
    // - if timestamp is less than 7 days ago: e.g. 12.01.2021 12:34
    if (!timestamp) {
        return '';
    }
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;
    // if it's less than 24 hours ago, return {duration} ago
    if (diff < 24 * 60 * 60 * 1000) {
        return formatDuration(Math.floor(diff / 1000)) + ' ago';
    }
    return date.toLocaleString();
}

function formatDuration(duration) {
    // Format duration (in seconds) to a human readable string, e.g. 10.2s, 1min 2.1s, 1h 2min 32s
    if (!duration) {
        return '';
    }
    let seconds = duration;
    let minutes = 0;
    let hours = 0;
    if (seconds > 60) {
        minutes = Math.floor(seconds / 60);
        seconds = seconds % 60;
    }
    if (minutes > 60) {
        hours = Math.floor(minutes / 60);
        minutes = minutes % 60;
    }
    let formatted = '';
    if (hours) {
        formatted += `${hours}h `;
    }
    if (minutes) {
        formatted += `${minutes}min `;
    }
    if (seconds) {
        // round to 1 decimal
        seconds = Math.round(seconds * 10) / 10;
        formatted += `${seconds}s`;
    }
    return formatted;
}


function formatMaybeDuration(duration) {
    if (!duration) {
        return '';
    }
    return 'Finished in ' + formatDuration(duration);
}

function formatCost(cost) {
    if (!cost) {
        return '';
    }
    return 'Cost: ' + cost;
}


function sendMessageMeta(path, meta, token) {
    // Send PUT request to /messages/{path} with meta data
    fetch(`http://localhost:8745/meta/${path[path.length - 1]}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + token,
        },
        body: JSON.stringify(meta),
    });

}



function ChatMessage({message, handleSubConversationClick, runCodeAfterMessage, saveCodeInMessage, forkFromMessage, token }){
    // if the message has not streamed enough, return
    if (!message.chat) {
        return '';
    }
    // if (message.chat.name === 'return') {
    //     return '';
    // }
    if (message.meta.deleted) {
        return '';
    }
    return (
        <div className={`message-${message.chat.role || 'assistant'}`} key={message.path[message.path.length - 1]}>
            <div className='message-header'>
                <div className='message-header-left'>
                    {message.chat.role } {message.chat.name} 
                    {' ' + formatTimestamp(message.meta.timestamp) + ' '} 
                    {formatMaybeDuration(message.meta.duration) + ' '}
                </div>
                <div className='message-header-right'>
                    <ForkRightIcon fontSize="small" onClick={() => {
                        forkFromMessage(message.path);
                    }} />
                    {message.meta.rating === 1 ? <ThumbUpIcon fontSize="small" /> : <ThumbUpOutlinedIcon fontSize="small" onClick={() => {
                        sendMessageMeta(message.path, {"rating": 1}, token);
                    }} />}
                    {message.meta.rating === -1 ? <ThumbDownIcon fontSize="small" /> : <ThumbDownOutlinedIcon fontSize="small" onClick={() => {
                        sendMessageMeta(message.path, {"rating": -1}, token);
                    }} />}
                    <CloseIcon onClick={() => {
                            sendMessageMeta(message.path, {"deleted": true}, token)
                        }}
                        fontSize="small" />
                </div>
            </div>
            {functionsToRenderAsCode.includes(message.chat.name) ? (
                <CodeBlock
                    code={message.chat.content}
                    runnable={false}
                    editable={false}
                /> ) : (
                <DisplayJson data={message.chat.content} run={runCodeAfterMessage(message)}/>
            )}

            {message.meta.display_data && message.meta.display_data.map((data, index) => {
                return <DisplayData key={index} data={data} />;
            })}
            {message.chat.function_call && <DisplayJson data={message.chat.function_call} editable={true}  run={runCodeAfterMessage(message)} save={saveCodeInMessage(message)}/>}
            {message.meta.children?.map(subConversationId => {
                return (
                    <div onClick={() => handleSubConversationClick(subConversationId)}><i>View thread</i></div>
                );
            })}
            <div className="message-footer">
                {formatCost(message.meta.cost) + ' '} 
                {formatMaybeDuration(message.meta.duration) + ' '}
            </div>
        </div>
    );
}


export default ChatMessage;