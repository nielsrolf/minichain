import React, { useState, useEffect } from "react";
import { w3cwebsocket as W3CWebSocket } from "websocket";
import './ChatApp.css';
import DisplayJson from './DisplayJson';





const ChatApp = () => {
    const [client, setClient] = useState(null);
    const [connectionStatus, setConnectionStatus] = useState("DISCONNECTED");
    const [inputValue, setInputValue] = useState("");
    const [path, setPath] = useState(["root"]);

    const [conversationTree, setConversationTree] = useState({
        conversations: { root: [] },
        subConversations: {},
        lastMessageId: null,
    });

    useEffect(() => {
        const client = new W3CWebSocket('ws://localhost:8000/ws/webgpt');

        client.onopen = () => {
            console.log('WebSocket Client Connected');
            setConnectionStatus("CONNECTED");
        };

        client.onerror = (error) => {
            console.log('Connection Error:', error);
            setConnectionStatus("ERROR");
        };

        client.onclose = (event) => {
            console.log('WebSocket Client Closed', event);
            setConnectionStatus("CLOSED");
        };

        client.onmessage = (message) => {
            const data = JSON.parse(message.data);
            console.log({ data })
            switch (data.type) {
                case "start":
                    if (data.conversation_id) {
                        console.log("Starting new conversation: " + data.conversation_id);
                        setConversationTree(prevConversationTree => {
                            const { conversations, subConversations, lastMessageId } = prevConversationTree;
                            return {
                                conversations: { ...conversations, [data.conversation_id]: [] },
                                subConversations: { ...subConversations, [lastMessageId]: data.conversation_id },
                                lastMessageId: lastMessageId
                            };
                        });
                        //   setpath[path.length - 1](data.conversation_id);
                        //   setConversations({...conversations, [data.conversation_id]: []});
                        //   setSubConversations({...subConversations, [lastMessageId]: data.conversation_id});
                    } else {
                        // we are starting to stream a message. 
                        // TODO
                        console.log("Starting to stream a message - not implemented", data);
                    }
                    break;
                case "end":
                    if (data.conversation_id) {
                        // set active conversation to parent conversation
                        setPath(prevPath => {
                            const newPath = [...prevPath];
                            if (newPath[newPath.length - 1] === data.conversation_id) {
                                newPath.pop();
                            }
                            return newPath;
                        });
                    } else {
                        // we are ending a stream of messages.
                        // TODO
                        console.log("Ending a stream of messages - not implemented", data);
                    }
                    break;
                default:
                    console.log("Adding to conv tree: " + message.data);
                    const { id } = data;
                    setConversationTree(prevConversationTree => {
                        const { conversations, subConversations } = prevConversationTree;
                        const newConversation = conversations[data.conversation_id] || [];
                        return {
                            conversations: { ...conversations, [data.conversation_id]: [...newConversation, data] },
                            subConversations: subConversations,
                            lastMessageId: id
                        };
                    });
                    pusToPath(data.conversation_id);
            }
        };

        setClient(client);

        return () => {
            client.close();
        };
    }, []);

    // Function to handle when a message with a sub conversation is clicked
    const handleSubConversationClick = (messageId) => {
        const subConversationId = conversationTree.subConversations[messageId];
        console.log("clicked on sub conversation: " + subConversationId + " for message: " + messageId + "")
        if (subConversationId) {
            pusToPath(subConversationId);
        }
    };

    const sendMessage = () => {
        if (client.readyState !== client.OPEN) {
            console.error("Client is not connected");
            return;
        }

        const messagePayload = JSON.stringify({ query: inputValue, response_to: conversationTree.lastMessageId });
        client.send(messagePayload);
        setInputValue("");
    };

    const pusToPath = (id) => {
        setPath(prevPath => {
            // if we are already on that path, do nothing
            if (prevPath[prevPath.length - 1] === id) {
                return prevPath;
            }
            // otherwise push the path to the stack
            return [...prevPath, id]
        });
        // setpath[path.length - 1](id);
        console.log("Setting display conversation id to " + id);
    };

    console.log({ conversationTree });


    return (
        <div className="main">
            {connectionStatus !== "CONNECTED" && <div className="disconnected">Connection: {connectionStatus}</div>}
            <div className="header">
                <button onClick={() => pusToPath("root")}>Back to root</button>
                <button onClick={() => {
                    if (path.length > 1) {
                        setPath(prevPath => prevPath.slice(0, prevPath.length - 1));
                    }
                }}>Back </button>
                {Object.keys(conversationTree.conversations).map(conversationId => 
                    <button onClick={() => pusToPath(conversationId)}>{conversationId}</button>
                )}
            </div>
            <div style={{ height: "50px" }}></div>

            <div>
                {conversationTree.conversations[path[path.length - 1]] && conversationTree.conversations[path[path.length - 1]].map((message, index) =>
                    <div className={`message-${message.role}`} key={index} onClick={() => handleSubConversationClick(message.id)}>
                        {message.function_call && <DisplayJson data={message.function_call} />}
                        <DisplayJson data={message.content} />
                        {conversationTree.subConversations[message.id] && <div>Click to view sub conversation {conversationTree.subConversations[message.id]}</div>}
                    </div>
                )}
            </div>
            <div className="spacer"></div>
            <div className="input-area">
                <textarea className="user-input" value={inputValue} onChange={e => setInputValue(e.target.value)}></textarea>
                <button className="send-button" onClick={sendMessage}>Send</button>
            </div>
        </div>
    );
};

export default ChatApp;
