import React, { useState, useEffect, useMemo } from "react";
import { w3cwebsocket as W3CWebSocket } from "websocket";
import './ChatApp.css';
import ChatMessage from "./ChatMessage";
import ArrowBackIcon from '@mui/icons-material/ArrowBack';



function addDiffToMessage(message, diff) {
    if (!message) {
        return diff;
    }
    // if both values are strings, add the diff
    if (typeof message === "string" && typeof diff === "string") {
        return message + diff;
    }
    // add the diff recursively to message
    let updated = { ...message }
    for (const key in diff) {
        updated[key] = addDiffToMessage(message[key], diff[key]);
    }
    return updated;
}


const ChatApp = () => {
    const [client, setClient] = useState(null);
    const [connectionStatus, setConnectionStatus] = useState("DISCONNECTED");
    const [checkConnectionStatus, setCheckConnectionStatus] = useState(false);
    const [inputValue, setInputValue] = useState("");
    const [defaultAgentName, setDefaultAgentName] = useState("ChatGPT");
    const [isAttached, setIsAttached] = useState(true);
    const [availableAgents, setAvailableAgents] = useState([]);
    const [showInitMessages, setShowInitMessages] = useState(false);
    const [streamingState, setStreamingState] = useState({
        idToPath: {},
        messages: {},
        lastMessagePath: ['root']
    });

    const [path, setPath] = useState(["root"]);
    const [conversation, setConversation] = useState({
        path: ["root"],
        messages: []
    });

    const currentConversationId = useMemo(() => path[path.length - 1], [path]);

    // fetch the available agents
    useEffect(() => {
        fetch("http://localhost:8745/agents")
            .then(response => response.json())
            .then(data => {
                setAvailableAgents(data);
            })
            .catch(e => {
                console.error(e);
            });
    }, []);

    // fetch the history
    useEffect(() => {
        fetch("http://localhost:8745/messages/" + path[path.length - 1])
            .then(response => response.json())
            .then(conversation => {
                // setConversation(conversation);
                setStreamingState(prev => {
                    const { lastMessagePath } = prev;
                    // for each message in the conversation, add it to the dicts
                    const idToPath = {};
                    const messages = {};
                    conversation.messages.forEach(message => {
                        idToPath[message.path[message.path.length - 1]] = message.path
                        messages[message.path[message.path.length - 1]] = message;
                    });
                    return {
                        idToPath: idToPath,
                        messages: messages,
                        lastMessagePath: lastMessagePath
                    };
                });
                setConversation(conversation);
            })
            .catch(e => {
                console.error(e);
            });
    }, [path]);



    useEffect(() => {
        // get the agent name from the URL
        const client = new W3CWebSocket(`ws://127.0.0.1:8745/ws`);

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

        client.onmessage = (messageRaw) => {
            const message = JSON.parse(messageRaw.data);
            /**
             * message = {
                "type": "path",
                "path": self.path,
                "meta": self.meta
            }

            {
                "id": self.path[-1],
                "type": "set",
                "chat": self.current_message,
                "meta": self.meta
            }

            {
                "id": self.path[-1],
                "type": "chunk",
                "diff": diff
            }
            */
            if (message.type === "path") {
                setStreamingState(prev => {
                    const idToPath = prev.idToPath;
                    const messages = prev.messages;
                    idToPath[message.path[message.path.length - 1]] = message.path;
                    messages[message.path[message.path.length - 1]] = { meta: message.meta, path: message.path };
                    return {
                        idToPath: idToPath,
                        messages: messages,
                        lastMessagePath: message.path
                    };
                });

            } else if (message.type === "set") {
                // update or create the message if it is in the current conversation
                // otherwise, do nothing
                setStreamingState(prev => {
                    const path = prev.idToPath[message.id];
                    if (!path) {
                        return prev;
                    }
                    const idToPath = { ...prev.idToPath };
                    const messages = { ...prev.messages };
                    messages[message.id] = { meta: message.meta, path: idToPath[message.id], chat: message.chat };
                    return {
                        idToPath: idToPath,
                        messages: messages,
                        lastMessagePath: path
                    };
                });

            } else if (message.type === "chunk") {
                setStreamingState(prev => {
                    const path = prev.idToPath[message.id];
                    const currentMessage = prev.messages[message.id];
                    if (!currentMessage) {
                        console.log("no current message", message, prev.messages);
                        return prev;
                    }
                    const newMessage = addDiffToMessage(currentMessage, { chat: message.diff });
                    const idToPath = { ...prev.idToPath };
                    const messages = { ...prev.messages };
                    messages[message.id] = newMessage;
                    return {
                        idToPath: idToPath,
                        messages: messages,
                        lastMessagePath: path
                    };
                });
            } else {
                console.error("Unknown message type", message);
            }
        };

        setClient(client);

        return () => {
            client.close();
        };
    }, []);


    // when the streaming state updates: update the conversation
    useEffect(() => {
        const { messages } = streamingState;
        setConversation(prevConversation => {
            // todo only update with messages that belong to the prevConversation
            const newMessages = [...prevConversation.messages];
            for (let updated of Object.values(messages)) {
                if (updated.path[updated.path.length - 2] !== prevConversation.path[prevConversation.path.length - 1]) {
                    continue;
                }
                const updatedId = updated.path[updated.path.length - 1];
                const existingMessage = newMessages.find(i => i.path[i.path.length - 1] === updatedId);
                if (existingMessage) {
                    existingMessage.chat = updated.chat;
                    existingMessage.meta = updated.meta;
                } else {
                    newMessages.push(updated);
                }
            }
            return {
                ...prevConversation,
                messages: newMessages
            };
        });
    }, [streamingState]);

    // when the streaming state noticed a message not in the conversation, update the path (if we are attached)
    useEffect(() => {
        const lastMessagePath = streamingState.lastMessagePath;
        if (
            isAttached &&
            lastMessagePath[lastMessagePath.length - 2] &&
            lastMessagePath[lastMessagePath.length - 2] !== path[path.length - 1]
        ) {
            console.log("calling setPath because new message and we are attached")
            setPath([...path, lastMessagePath[lastMessagePath.length - 2]]);
        }
    }, [streamingState, isAttached, path]);



    // Function to handle when a message with a sub conversation is clicked
    const handleSubConversationClick = (subConversationId) => {
        setIsAttached(false);
        if (!subConversationId) {
            // just refresh this conversation
            setPath([...path]);
        }
        if (subConversationId) {
            pushToPath(subConversationId);
        }
    };

    const sendMessage = () => {
        if (client.readyState !== client.OPEN) {
            console.error("Client is not connected");
            return;
        }
        let response_to = null;
        const currentConversationId = path[path.length - 1];
        if (currentConversationId !== "root") {
            response_to = currentConversationId;
        }

        const messagePayload = JSON.stringify({ query: inputValue, response_to: response_to, agent: conversation.meta.agent || defaultAgentName });
        client.send(messagePayload);
        setInputValue("");
        setIsAttached(true);
    };

    const pushToPath = (id) => {
        console.log("pushing to path", id);
        setPath(prevPath => {
            // if we are already on that path, do nothing
            if (prevPath[prevPath.length - 1] === id) {
                return prevPath;
            }
            // otherwise push the path to the stack
            return [...prevPath, id]
        });
    };


    const selectAgent = (agentName) => {
        setDefaultAgentName(agentName);
    }

    // if the connection is not connected after 1 second, try to reload the page
    setTimeout(() => {
        setCheckConnectionStatus(true);
    }, 1000);
    useEffect(() => {
        if (checkConnectionStatus && connectionStatus !== "CONNECTED") {
            window.location.reload();
        }
    }, [checkConnectionStatus, connectionStatus]);


    if (connectionStatus !== "CONNECTED") {
        return (
            <div className="main">
                <div className="header">
                    minichain is {connectionStatus} :(
                </div>
                <div style={{ height: "100px" }}></div>
                <div className="chat">
                    You need to manually start the backend via `python -m minichain.api` and have Docker running. Then refresh the page.
                </div>
            </div>
        );
    }

    return (
        <div className="main">
            <div className="header">
                <ArrowBackIcon onClick={() => {
                    setIsAttached(false);
                    if (path.length === 1) {
                        return;
                    }
                    setPath(prevPath => prevPath.slice(0, prevPath.length - 1));
                }} />
                <button onClick={() => {
                    setIsAttached(false);
                    pushToPath("root")
                }}>Main</button>
                <button onClick={() => {
                    // parent
                    setIsAttached(false);
                    const parent = conversation.path[conversation.path.length - 3] || "root";
                    pushToPath(parent);
                }}>Parent</button>
                {isAttached ? <button id="attachDetach" onClick={() => setIsAttached(false)}>Detach</button> : <button onClick={() => {
                    setIsAttached(true);
                }}>Attach</button>}
                <button onClick={() => {
                    // Scroll to the last message using scrollIntoView
                    const bottom = document.getElementById("bottom");
                    bottom?.scrollIntoView({ behavior: "smooth" });
                }}>Down</button>
                <button onClick={() => {
                    // Send a cancel message to the websocket
                    client.send(`cancel:${currentConversationId}}`);
                }}>Interrupt</button>
                {/* <button onClick={() => setGraphToggle(prev => !prev)}>Toggle Graph</button> */}
                <button onClick={() => setShowInitMessages(prev => !prev)}>Toggle Init Messages</button>
                {currentConversationId}
                {path[path.length - 1] === "root" && (
                    <select value={defaultAgentName} onChange={e => selectAgent(e.target.value)} style={{
                        position: "absolute",
                        right: "10px",
                        top: "10px",
                        backgroundColor: "black",
                        color: "white",
                        padding: "5px",
                    }}>
                        {availableAgents.map(agentName => <option value={agentName}>{agentName}</option>)}
                    </select>
                )}
                {/* otherwise show the current agent */}
                {path[path.length - 1] !== "root" && (
                    <div style={{
                        position: "absolute",
                        right: "10px",
                        top: "10px",
                        backgroundColor: "black",
                        color: "white",
                        padding: "5px",
                    }}>
                        {conversation.meta.agent || defaultAgentName}
                    </div>
                )}

            </div>
            <div style={{ height: "50px" }}></div>

            <div className="chat">
                {conversation.messages.filter(message => !message.meta?.is_initial || showInitMessages).map(message => {
                    if (message.agent && message.agent !== defaultAgentName) {
                        // message.agent is only set in the root conversation
                        return '';
                    }
                    if (message.meta.deleted) {
                        return '';
                    }
                    return (
                        <ChatMessage
                            message={message}
                            handleSubConversationClick={handleSubConversationClick}
                        />
                    );
                })
                }
                <div id="bottom"></div> {/* this is used to scroll to the bottom when a new message is added */}
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
