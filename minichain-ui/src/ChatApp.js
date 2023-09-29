import React, { useState, useEffect } from "react";
import { w3cwebsocket as W3CWebSocket } from "websocket";
import './ChatApp.css';
import DisplayJson from './DisplayJson';
import CodeBlock from "./CodeBlock";



const functionsToRenderAsCode = [
    "bash",
    "python",
    "view",
    "edit",
    "view_symbol",
    "replace_symbol",
];


function addDiffToMessage(message, diff) {
    console.log("addDiffToMessage", message, diff);
    if (!message) {
        return diff;
    }
    // if both values are strings, add the diff
    if (typeof message === "string" && typeof diff === "string") {
        return message + diff;
    }
    // add the diff recursively to message
    for (const key in diff) {
        message[key] = addDiffToMessage(message[key], diff[key]);
    }
    return message
}


const ChatApp = () => {
    const [client, setClient] = useState(null);
    const [connectionStatus, setConnectionStatus] = useState("DISCONNECTED");
    const [inputValue, setInputValue] = useState("");
    const [path, setPath] = useState(["root"]);
    const [agentName, setAgentName] = useState("yopilot");
    const [defaultAgentName, setDefaultAgentName] = useState("yopilot");
    const [isAttached, setIsAttached] = useState(true);
    const [minBottomTop, setMinBottomTop] = useState(0);
    const [availableAgents, setAvailableAgents] = useState([]);
    const [messages, setMessages] = useState([]);
    const [childrenOf, setChildrenOf] = useState({}); // childrenOf[conversationId] = [...messageIds]

    // fetch the available agents
    useEffect(() => {
        fetch("http://localhost:8000/agents")
            .then(response => response.json())
            .then(data => {
                setAvailableAgents(data);
            });
    }, []);

    // fetch the history
    useEffect(() => {
        fetch("http://localhost:8000/history")
            .then(response => response.json())
            .then(data => {
                console.log("history", data);
                // set the messages
                console.log("setMessages", setMessages);
                setMessages(data.messages);
                // the above gives a 'setMessages is not a function' error
                // so we use the below instead
                
                // set the childrenOf
                setChildrenOf(data.childrenOf);
            });
    }, [setMessages, setChildrenOf]);

    useEffect(() => {
        // get the agent name from the URL
        const client = new W3CWebSocket(`ws://localhost:8000/ws`);

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
            // check if it's
            // - a stack message
            // - message update
            // - a message chunk
            if (message.type === "stack") {
                // each message starts with a stack message that tells us where in the tree the message belongs
                const { stack } = message;
                setChildrenOf(prevChildrenOf => {
                    const newChildrenOf = { ...prevChildrenOf };
                    // iterate over the stack
                    let parent = stack[0];
                    for (let i = 1; i < stack.length; i++) {
                        const child = stack[i];
                        if (newChildrenOf[parent]) {
                            if (!newChildrenOf[parent].includes(child)) {
                                newChildrenOf[parent].push(child);
                            }
                        } else {
                            newChildrenOf[parent] = [child];
                        }
                        parent = child;
                    }
                    return newChildrenOf;
                });
            } else if (message.type === "message") {
                setMessages(prevMessages => {
                    const newMessages = [...prevMessages];
                    // if the message already exists, update it
                    const existingMessageIndex = newMessages.findIndex(i => i.id === message.data.id);
                    if (existingMessageIndex !== -1) {
                        newMessages[existingMessageIndex] = message.data;
                    } else {
                        newMessages.push(message.data);
                    }
                    return newMessages;
                });
            } else if (message.type === "chunk") {
                // if the message already exists, update it
                setMessages(prevMessages => {
                    const newMessages = [...prevMessages];
                    const existingMessageIndex = newMessages.findIndex(i => i.id === message.id);
                    if (existingMessageIndex !== -1) {
                        // add the diff to the existing message
                        console.log("before add diff", newMessages[existingMessageIndex], message)
                        newMessages[existingMessageIndex] = addDiffToMessage(newMessages[existingMessageIndex], message.diff);
                        console.log("after add diff", newMessages[existingMessageIndex])
                    } else {
                        newMessages.push({"id": message.id, ...message.diff});
                    }
                    return newMessages;
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

    // // when the user scrolls up, detach
    const detachOnScrollUp = () => {
        const handleScrollUp = () => {
            const bottom = document.getElementById("bottom");
            if (bottom) {
                const rect = bottom.getBoundingClientRect();
                console.log("bottom rect", rect, rect.top)

                if (rect.top > minBottomTop) {
                    setIsAttached(false);
                } else if(rect.top < minBottomTop) {
                    setMinBottomTop(rect.top);
                }
            }
        }
        window.addEventListener("scroll", handleScrollUp);
        return () => {
            window.removeEventListener("scroll", handleScrollUp);
        }
    };
    // run this shorty after the component is mounted
    useEffect(detachOnScrollUp, []);

    // Function to handle when a message with a sub conversation is clicked
    const handleSubConversationClick = (subConversationId) => {
        console.log("clicked on sub conversation: " + subConversationId)
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

        const messagePayload = JSON.stringify({ query: inputValue, response_to: response_to, agent: agentName });
        client.send(messagePayload);
        setInputValue("");
        setIsAttached(true);
    };

    const pushToPath = (id) => {
        setPath(prevPath => {
            // if we are already on that path, do nothing
            if (prevPath[prevPath.length - 1] === id) {
                return prevPath;
            }
            // otherwise push the path to the stack
            return [...prevPath, id]
        });
        // Scroll to the bottom of the page
        const bottom = document.getElementById("bottom");
        // If we open a new conversation the upscroll detection will notice we are higher than the bottom and detach
        // so we need to set the minBottomTop to a really high value
        if (bottom) {
            const rect = bottom.getBoundingClientRect();
            console.log("bottom rect", rect, rect.top)
            setMinBottomTop(rect.top + 100000);
        }
        bottom?.scrollIntoView({ behavior: "smooth" });
    };


    const selectAgent = (agentName) => {
        setAgentName(agentName);
        setDefaultAgentName(agentName);
    }

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

    const getMessages = (conversationId, messages, childrenOf) => {
        if (!messages) {
            return [];
        }
        console.log("getMessages", conversationId, messages, childrenOf);
        const messagesForConversation = messages.filter(message => childrenOf[conversationId].includes(message.id));
        // sort the messages by id
        console.log("messagesForConversation", messagesForConversation);
        return messagesForConversation;
    }

    return (
        <div className="main">
            <div className="header">
                <button onClick={() => pushToPath("root")}>Main</button>
                <button onClick={() => {
                    if (path.length > 1) {
                        setPath(prevPath => prevPath.slice(0, prevPath.length - 1));
                    }
                }}>Back </button>
                <button onClick={() => {
                    // parent
                    const currentConversationId = path[path.length - 1];
                    if (currentConversationId !== "root") {
                        const parent = Object.keys(childrenOf).find(key => childrenOf[key].includes(currentConversationId));
                        pushToPath(parent);
                    }
                }}>Parent</button>
                {isAttached ? <button id="attachDetach" onClick={() => setIsAttached(false)}>Detach</button> : <button onClick={() => {
                    setIsAttached(true);
                    const bottom = document.getElementById("bottom");
                    if (bottom) {
                        const rect = bottom.getBoundingClientRect();
                        console.log("bottom rect", rect, rect.top)
                        setMinBottomTop(rect.top);
                    }
                }}>Attach</button>}
                <button onClick={() => {
                    // Scroll to the last message using scrollIntoView
                    const bottom = document.getElementById("bottom");
                    bottom?.scrollIntoView({ behavior: "smooth" });
                }}>Scroll to Last Message</button>
                <button onClick={() => {
                    // Send a cancel message to the websocket
                    client.send('cancel');
                }}>Interrupt</button>
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
                        {agentName}
                    </div>
                )}

            </div>
            <div style={{ height: "50px" }}></div>

            <div className="chat">
                {getMessages(path[path.length - 1], messages, childrenOf).map(message => {
                    return (
                        <div className={`message-${message.role}`} key={message.id}>
                            {functionsToRenderAsCode.includes(message.name) ? <CodeBlock code={message.content} /> : <DisplayJson data={message.content} />}
                            {message.function_call && <DisplayJson data={message.function_call} />}
                            {childrenOf[message.id] && childrenOf[message.id].map(subConversationId => {
                                return (
                                    <div onClick={() => handleSubConversationClick(subConversationId)}>View thread</div>
                                );
                            })}
                        </div>
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
