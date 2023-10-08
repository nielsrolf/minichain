import DisplayJson from './DisplayJson';
import CodeBlock from "./CodeBlock";
import './ChatApp.css';


const functionsToRenderAsCode = [
    "bash",
    "python",
    "view",
    "edit",
    "view_symbol",
    "replace_symbol",
];


function ChatMessage({message, handleSubConversationClick }){
    // if the message has not streamed enough, return
    if (!message.chat) {
        return '';
    }
    if (message.role === 'function' && message.name === 'return') {
        return '';
    }
    return (
        <div className={`message-${message.chat.role || 'assistant'}`} key={message.path[message.path.length - 1]}>
            <div className='message-header'> {message.path[message.path.length - 1]} {message.chat.role } {message.chat.name} {message.meta.timestamp} {message.meta.cost} {message.meta.duration}</div>
            {functionsToRenderAsCode.includes(message.chat.name) ? <CodeBlock code={message.chat.content} /> : <DisplayJson data={message.chat.content} />}
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