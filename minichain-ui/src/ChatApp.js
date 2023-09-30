import React, { useState, useEffect, useMemo } from "react";
import { w3cwebsocket as W3CWebSocket } from "websocket";
import './ChatApp.css';
import ChatMessage from "./ChatMessage";
import ConversationTree from "./ConversationTree";






function addDiffToMessage(message, diff) {
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
    const [checkConnectionStatus, setCheckConnectionStatus] = useState(false);
    const [inputValue, setInputValue] = useState("");
    const [path, setPath] = useState(["root"]);
    const [agentName, setAgentName] = useState("yopilot");
    const [defaultAgentName, setDefaultAgentName] = useState("yopilot");
    const [isAttached, setIsAttached] = useState(true);
    const [minBottomTop, setMinBottomTop] = useState(0);
    const [availableAgents, setAvailableAgents] = useState([]);
    const [convTree, setConvTree] = useState({
        "messages": [],
        "childrenOf": {}
    });
    const [graphToggle, setGraphToggle] = useState(false);

    const currentConversationId = useMemo(() => path[path.length - 1], [path]);
    const visibleMessages = useMemo(() => {
        return convTree.messages.filter(message => convTree.childrenOf[currentConversationId]?.includes(message.id));
    }, [convTree, currentConversationId]);

    // fetch the available agents
    useEffect(() => {
        fetch("http://localhost:8000/agents")
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
        fetch("http://localhost:8000/history")
            .then(response => response.json())
            .then(data => {
                setConvTree(data);
            })
            .catch(e => {
                console.error(e);
            });
    }, []);


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
            setConvTree(prevConvTree => {
                let updatedMessages = [...prevConvTree.messages];
                let updatedChildrenOf = { ...prevConvTree.childrenOf };

                if (message.type === "stack") {
                    const { stack } = message;
                    let parent = stack[0];
                    for (let i = 1; i < stack.length; i++) {
                        const child = stack[i];
                        if (updatedChildrenOf[parent]) {
                            if (!updatedChildrenOf[parent].includes(child)) {
                                updatedChildrenOf[parent].push(child);
                            }
                        } else {
                            updatedChildrenOf[parent] = [child];
                        }
                        parent = child;
                    }
                } else if (message.type === "message") {
                    const existingMessageIndex = updatedMessages.findIndex(i => i.id === message.data.id);
                    if (existingMessageIndex !== -1) {
                        updatedMessages[existingMessageIndex] = message.data;
                    } else {
                        updatedMessages.push(message.data);
                    }
                } else if (message.type === "chunk") {
                    const existingMessageIndex = updatedMessages.findIndex(i => i.id === message.id);
                    if (existingMessageIndex !== -1) {
                        updatedMessages[existingMessageIndex] = addDiffToMessage(updatedMessages[existingMessageIndex], message.diff);
                    } else {
                        updatedMessages.push({ "id": message.id, ...message.diff });
                    }
                } else {
                    console.error("Unknown message type", message);
                }
                console.log({ updatedMessages, updatedChildrenOf })
                return {
                    "messages": updatedMessages,
                    "childrenOf": updatedChildrenOf
                };
            });
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
    };

    useEffect(() => {
        if (!isAttached) {
            return;
        }
        // Scroll to the bottom of the page
        const bottom = document.getElementById("bottom");
        // If we open a new conversation the upscroll detection will notice we are higher than the bottom and detach
        // so we need to set the minBottomTop to a really high value
        if (bottom) {
            const rect = bottom.getBoundingClientRect();
            setMinBottomTop(rect.top + 100000);
        }
        // if bottom is not in view, scroll to it
        if (!bottom || bottom.getBoundingClientRect().top > window.innerHeight) {
            bottom?.scrollIntoView({ behavior: "smooth" })
            setIsAttached(true);
        }
    }, [visibleMessages, isAttached]);


    useEffect(() => {
        if (!isAttached || convTree.messages.length === 0) {
            return;
        }
        // if we are attached and a new message has been send, push its conversation to the path
        const lastMessage = convTree.messages[convTree.messages.length - 1];
        if (!convTree.childrenOf[currentConversationId]?.includes(lastMessage.id)) {
            // find the conversation id
            const conversationId = Object.keys(convTree.childrenOf).find(key => convTree.childrenOf[key].includes(lastMessage.id));
            if (conversationId) {
                pushToPath(conversationId);
            }
        }
    }, [convTree, isAttached, currentConversationId]);



    const selectAgent = (agentName) => {
        setAgentName(agentName);
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
                <button onClick={() => {
                    setIsAttached(false);
                    pushToPath("root")
                }}>Main</button>
                <button onClick={() => {
                    setIsAttached(false);
                    setPath(prevPath => prevPath.slice(0, prevPath.length - 1));
                }}>Back </button>
                <button onClick={() => {
                    // parent
                    setIsAttached(false);
                    const currentConversationId = path[path.length - 1];
                    if (currentConversationId !== "root") {
                        const parent = Object.keys(convTree.childrenOf).find(key => convTree.childrenOf[key].includes(currentConversationId));
                        const grandParent = Object.keys(convTree.childrenOf).find(key => convTree.childrenOf[key].includes(parent));
                        pushToPath(grandParent);
                    }
                    
                }}>Parent</button>
                {isAttached ? <button id="attachDetach" onClick={() => setIsAttached(false)}>Detach</button> : <button onClick={() => {
                    setIsAttached(true);
                    const bottom = document.getElementById("bottom");
                    if (bottom) {
                        const rect = bottom.getBoundingClientRect();
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
                {/* <button onClick={() => setGraphToggle(prev => !prev)}>Toggle Graph</button> */}
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
                        {agentName}
                    </div>
                )}

            </div>
            {/* {graphToggle && (
                <ConversationTree convTree={convTree} path={path} pushToPath={pushToPath} />
            )} */}
            <div style={{ height: "50px" }}></div>

            <div className="chat">
                {visibleMessages.map(message => {
                    return (
                        <ChatMessage
                            message={message}
                            convTree={convTree}
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
