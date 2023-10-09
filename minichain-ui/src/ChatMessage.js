import DisplayJson from './DisplayJson';
import CodeBlock from "./CodeBlock";
import './ChatApp.css';
import { func } from 'prop-types';


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
    if (data['image/png']) {
        return <div class='media-container'><img src={`data:image/png;base64,${data['image/png']}`} alt={`${data['text/plain']}`} /></div>;
    }
    if (data['text/html']) {
        return <div dangerouslySetInnerHTML={{ __html: data['text/html'] }} />;
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

function ChatMessage({message, handleSubConversationClick }){
    // if the message has not streamed enough, return
    if (!message.chat) {
        return '';
    }
    if (message.chat.name === 'return') {
        return '';
    }
    return (
        <div className={`message-${message.chat.role || 'assistant'}`} key={message.path[message.path.length - 1]}>
            <div className='message-header'>
                {message.chat.role } {message.chat.name} 
                {' ' + formatTimestamp(message.meta.timestamp) + ' '} 
                {formatCost(message.meta.cost) + ' '} 
                {formatMaybeDuration(message.meta.duration) + ' '}
            </div>
            {functionsToRenderAsCode.includes(message.chat.name) ? <CodeBlock code={message.chat.content} /> : <DisplayJson data={message.chat.content} />}
            {message.meta.display_data && message.meta.display_data.map((data, index) => {
                return <DisplayData key={index} data={data} />;
            })}
            {message.chat.function_call && <DisplayJson data={message.chat.function_call} />}
            {message.children?.map(subConversationId => {
                return (
                    <div onClick={() => handleSubConversationClick(subConversationId)}><i>View thread</i></div>
                );
            })}
        </div>
    );
}


export default ChatMessage;