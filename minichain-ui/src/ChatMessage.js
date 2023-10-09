import DisplayJson from './DisplayJson';
import CodeBlock from "./CodeBlock";
import './ChatApp.css';


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
        return <img src={`data:image/png;base64,${data['image/png']}`} alt={`${data['text/plain']}`} />;
    }
    if (data['text/html']) {
        return <div dangerouslySetInnerHTML={{ __html: data['text/html'] }} />;
    }
    console.log("cannot display data:");
    console.log(data);
    
}

function ChatMessage({message, handleSubConversationClick }){
    // if the message has not streamed enough, return
    console.log(message.meta);
    if (!message.chat) {
        return '';
    }
    if (message.chat.name === 'return') {
        return '';
    }
    return (
        <div className={`message-${message.chat.role || 'assistant'}`} key={message.path[message.path.length - 1]}>
            <div className='message-header'> {message.path[message.path.length - 1]} {message.chat.role } {message.chat.name} {message.meta.timestamp} {message.meta.cost} {message.meta.duration}</div>
            {functionsToRenderAsCode.includes(message.chat.name) ? <CodeBlock code={message.chat.content} /> : <DisplayJson data={message.chat.content} />}
            {message.meta.display_data && message.meta.display_data.map((data, index) => {
                return <DisplayData key={index} data={data} />;
            })}
            {message.chat.function_call && <DisplayJson data={message.chat.function_call} />}
            {message.children?.map(subConversationId => {
                return (
                    <div onClick={() => handleSubConversationClick(subConversationId)}>View thread</div>
                );
            })}
        </div>
    );
}


export default ChatMessage;