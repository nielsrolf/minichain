import React, { useState, useEffect, useRef, useCallback } from 'react';
// import WebSocket from 'react-websocket';
import useWebSocket, { ReadyState } from 'react-use-websocket';


const WebSocketChat = () => {

    const [currentConversationId, setCurrentConversationId] = useState("main");
    const [conversations, setConversations] = useState({ main: { messages: [] } });
    const [subConversations, setSubConversations] = useState({}); // [subConversationId: string]: { messages: Message[] }
    const [inputValue, setInputValue] = useState('');

    const socketUrl = 'ws://localhost:8000/ws/webgpt';

    const { sendMessage, lastMessage, readyState } = useWebSocket(socketUrl);

    

    

    useEffect(() => {
        const handleMessage = (message) => {
            console.log({ message })
            // let message = JSON.parse(data);
            // Parse the incoming message and update the state based on its contents
            if (message.type === 'start') {
                // Initialize a new conversation
                const previousMsgId = conversations[currentConversationId]?.id || 'main';
                setConversations({
                    ...conversations,
                    [message.conversation_id]: {
                        messages: [],
                    },
                });
                setSubConversations({
                    ...subConversations,
                    [previousMsgId]: message.conversation_id,
                });
                console.log({
                    ...conversations,
                    [message.conversation_id]: {
                        messages: [],
                    },
                })
                setCurrentConversationId(message.conversation_id);
            } else if (message.type === 'end') {
                // set current conversation to parrent conversation: key of the value of the current conversation
                const parent = Object.keys(subConversations).find(key => subConversations[key].includes(currentConversationId));
                setCurrentConversationId(parent);
            } else {
                // Add a new message to the current conversation
                console.log({ message, currentConversationId, conversations })
                console.log(conversations[currentConversationId])
                setConversations({
                    ...conversations,
                    [currentConversationId]: {
                        ...conversations[currentConversationId],
                        messages: [
                            ...conversations[currentConversationId].messages,
                            message,
                        ],
                    },
                });
            }
        };
        if (lastMessage !== null) {
            const data = JSON.parse(lastMessage.data);
            handleMessage(data);
        }
    }, [lastMessage, conversations, currentConversationId, subConversations]);

    const handleInputChange = (event) => {
        setInputValue(event.target.value);
    };

    const handleSubmit = useCallback(() => {
        if (readyState === ReadyState.OPEN) {
            const message = { query: inputValue };
            sendMessage(JSON.stringify(message));
            setInputValue(''); // Clear the input field
        }
    }, [readyState, inputValue, sendMessage]);

    useEffect(() => {
        if (readyState === ReadyState.OPEN) {
            const heartbeatInterval = setInterval(() => {
                sendMessage(JSON.stringify({ type: 'heartbeat' }));
            }, 10000);

            return () => clearInterval(heartbeatInterval);
        }
    }, [readyState, sendMessage]);

    console.log({ conversations, currentConversationId, "selected": conversations[currentConversationId] });

    return (
        <div>
            <div>
                <button onClick={() => setCurrentConversationId('main')}>Back to main</button>
                {
                    conversations[currentConversationId] && (
                        <ChatConversation
                            conversation={conversations[currentConversationId]}
                            onSubConversationOpen={setCurrentConversationId}
                        />
                    )
                }
                <input type="text" value={inputValue} onChange={handleInputChange} />
                <button onClick={handleSubmit}>Send</button>
            </div>
            <div>The WebSocket is currently {ReadyState[readyState]}</div>
        </div>
    );
};


// const WebSocketChatOld = () => {
//     const [currentConversationId, setCurrentConversationId] = useState("main");
//     const [conversations, setConversations] = useState({ main: { messages: [] } });
//     const [subConversations, setSubConversations] = useState({}); // [subConversationId: string]: { messages: Message[] }
//     const [inputValue, setInputValue] = useState('');
//     const [wsOpen, setWsOpen] = useState(false);
//     const heartbeatIntervalId = useRef(null);
//     const wsRef = useRef(null);

//     const handleMessage = (data) => {
//         let message = JSON.parse(data);
//         // Parse the incoming message and update the state based on its contents
//         if (message.type === 'start') {
//             // Initialize a new conversation
//             setSubConversations({
//                 ...subConversations,
//                 [currentConversationId]: [
//                     ...subConversations[currentConversationId],
//                     message.conversationId,
//                 ]
//             });
//             setConversations({
//                 ...conversations,
//                 [message.conversationId]: {
//                     messages: [],
//                 },
//             });
//             setCurrentConversationId(message.conversationId);
//         } else if (message.type === 'message') {
//             // Add a new message to the current conversation
//             setConversations({
//                 ...conversations,
//                 [currentConversationId]: {
//                     ...conversations[currentConversationId],
//                     messages: [
//                         ...conversations[currentConversationId].messages,
//                         message,
//                     ],
//                 },
//             });
//         } else if (message.type === 'end') {
//             // set current conversation to parrent conversation: key of the value of the current conversation
//             const parent = Object.keys(subConversations).find(key => subConversations[key].includes(currentConversationId));
//             setCurrentConversationId(parent);
//         }
//     };

//     // useEffect(() => {
//     //     // Scroll to the bottom of the chat window
//     //     const chatWindow = document.getElementById('chat-window');
//     //     chatWindow.scrollTop = chatWindow.scrollHeight;
//     // });



//     const handleInputChange = (event) => {
//         setInputValue(event.target.value);
//     };


//     console.log({ conversations, subConversations, currentConversationId })

//     const [ws, setWs] = useState(null);

//     useEffect(() => {
//         const websocket = new WebSocket("ws://localhost:8000/ws/webgpt");

//         websocket.onopen = () => {
//             console.log("connected to websocket");
//             setWs(websocket);
//         };

//         websocket.onmessage = (event) => {
//             handleMessage(event.data);
//         };

//         websocket.onclose = () => {
//             console.log("disconnected from websocket");
//             setWs(null);
//         };

//         return () => {
//             websocket.close();
//         };
//     }, []);

//     const handleSubmit = () => {
//         if (ws) {
//             const message = { query: inputValue };
//             ws.send(JSON.stringify(message));
//             setInputValue(''); // Clear the input field
//         }
//     };

//     useEffect(() => {
//         const heartbeatInterval = setInterval(() => {
//             if (ws) {
//                 ws.send(JSON.stringify({ type: 'heartbeat' }));
//             }
//         }, 10000);

//         return () => clearInterval(heartbeatInterval);
//     }, [ws]);

//     return (
//         <div>
//             <div>
//                 <button onClick={() => setCurrentConversationId('main')}>Back to main</button>
//                 <ChatConversation
//                     conversation={conversations[currentConversationId]}
//                     onSubConversationOpen={setCurrentConversationId}
//                 />
//                 <input type="text" value={inputValue} onChange={handleInputChange} />
//                 <button onClick={handleSubmit}>Send</button>
//             </div>
//         </div>
//     );
// };

const ChatConversation = ({ conversation, onSubConversationOpen }) => {
    return (
        <div>
            {conversation.messages.map(message => (
                <ChatMessage
                    key={message.id}
                    message={message}
                    onSubConversationOpen={onSubConversationOpen(message.id)}
                />
            ))}
        </div>
    );
};

const ChatMessage = ({ message, onSubConversationOpen }) => {
    return (
        <div style={{border: "1px solid black"}}>
            <p>{message.content}</p>
            <button onClick={() => onSubConversationOpen(message.subConversationId)}>
                Open
            </button>
        </div>
    );
};

export default WebSocketChat;
