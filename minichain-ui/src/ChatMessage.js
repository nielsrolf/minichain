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


function ChatMessage({message, convTree, handleSubConversationClick }){
    if (message.role === 'function' && message.name === 'return') {
        return '';
    }
    return (
        <div className={`message-${message.role}`} key={message.id}>
            <div className='message-header'> {message.id} {message.role } {message.name} {message.time}</div>
            {functionsToRenderAsCode.includes(message.name) ? <CodeBlock code={message.content} /> : <DisplayJson data={message.content} />}
            {message.function_call && <DisplayJson data={message.function_call} />}
            {convTree.childrenOf[message.id] && convTree.childrenOf[message.id].map(subConversationId => {
                return (
                    <div onClick={() => handleSubConversationClick(subConversationId)}>View thread</div>
                );
            })}
        </div>
    );
}


export default ChatMessage;