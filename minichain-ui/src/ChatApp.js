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


const ChatApp = () => {
    const [client, setClient] = useState(null);
    const [connectionStatus, setConnectionStatus] = useState("DISCONNECTED");
    const [inputValue, setInputValue] = useState("");
    const [path, setPath] = useState(["root"]);
    const [agentName, setAgentName] = useState("yopilot");
    const [defaultAgentName, setDefaultAgentName] = useState("yopilot");
    const [isAttached, setIsAttached] = useState(true);
    const [minBottomTop, setMinBottomTop] = useState(0);

    const [conversationTree, setConversationTree] = useState({
        conversations: { root: [] },
        subConversations: {},
        parents: {},
        lastMessageId: null,
        agents: {}
    });

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

        client.onmessage = (message) => {
            console.log("message received", message);
            const data = JSON.parse(message.data);
            console.log({ data })
            switch (data.type) {
                case "start":
                    console.log("Starting new conversation: " + data.conversation_id);
                    if (data.conversation_id) {
                        // if we already have this conversation, stop
                        if (conversationTree.conversations[data.conversation_id]) {
                            console.log("Conversation already exists: " + data.conversation_id);
                            break;
                        }
                        console.log("Starting new conversation: " + data.conversation_id);
                        setConversationTree(prevConversationTree => {
                            const { conversations, subConversations, lastMessageId, parents, agents } = prevConversationTree;
                            // lets prepare to use "root.parent.child" as conversation ids
                            let activeConversationId = data.conversation_id.split(".")[0]
                            // but since it's not implemented everywhere, we also use the last message id
                            if (lastMessageId && !data.conversation_id.includes(".")) {
                                // get the conversation if of the last message
                                activeConversationId = Object.keys(conversations).find(conversationId => conversations[conversationId].map(message => message.id).includes(lastMessageId));
                            }
                            const siblings = subConversations[activeConversationId] || [];
                            console.log(`New conversation ${data.conversation_id} jas parent ${activeConversationId}`);
                            return {
                                conversations: { ...conversations, [data.conversation_id]: [] },
                                subConversations: { ...subConversations, [lastMessageId]: [...siblings, data.conversation_id] },
                                parents: { ...parents, [data.conversation_id]: activeConversationId },
                                lastMessageId: lastMessageId,
                                agents: { ...agents, [data.conversation_id]: data.agent }
                            };
                        });
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
                            if (newPath[newPath.length - 1] === data.conversation_id && newPath.length > 2 && newPath[newPath.length - 2] !== "root") {
                                newPath.pop();
                            }
                            return newPath;
                        });
                        setConversationTree(prevConversationTree => {
                            const { conversations, subConversations, parents, agents } = prevConversationTree;
                            let lastParentMessageId = null;
                            try {
                                lastParentMessageId = conversations[parents[data.conversation_id]].slice(-1)[0].id;
                            } catch (error) {
                                // we are at the root, we leave it as null
                            }
                            return {
                                conversations,
                                subConversations,
                                parents,
                                lastMessageId: lastParentMessageId,
                                agents
                            };
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
                        const { conversations, subConversations, parents, agents } = prevConversationTree;
                        const newConversation = conversations[data.conversation_id] || [];
                        const updatedConversation = [...newConversation.filter(i => i.id !== id), data];
                        return {
                            conversations: { ...conversations, [data.conversation_id]: updatedConversation},
                            subConversations,
                            parents,
                            lastMessageId: id,
                            agents
                        };
                    });
                    // if(isAttached){
                    // the above doesn't work because it's not updated yet, so we do it ugly and get the html inner state of the button
                    const button = document.getElementById("attachDetach");
                    if (button && button.innerHTML === "Detach") {
                        pushToPath(data.conversation_id);
                    }
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
        // setpath[path.length - 1](id);
        console.log("Setting display conversation id to " + id);
        // set the agent name to the agent of the conversation
        if(conversationTree.agents[id]){
            setAgentName(conversationTree.agents[id] || defaultAgentName);
        }
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

    console.log({ conversationTree });

    const selectAgent = (agentName) => {
        setAgentName(agentName);
        setDefaultAgentName(agentName);
        console.log({conversationTree})
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
                pushToPath(conversationTree.parents[currentConversationId]);
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

                {/* {Object.keys(conversationTree.conversations).map(conversationId => 
                    <button onClick={() => pushToPath(conversationId)}>{conversationId}</button>
                )} */}
                {/* on the right of the header, show the selected agent
                if we are on root, show the agent selection
                */}
                {path[path.length - 1]}
                {path[path.length - 1] === "root" && (
                    <select value={defaultAgentName} onChange={e => selectAgent(e.target.value)} style={{
                        position: "absolute",
                        right: "10px",
                        top: "10px",
                        backgroundColor: "black",
                        color: "white",
                        padding: "5px",
                    }}>
                        <option value="chatgpt">chatgpt</option>
                        <option value="yopilot">yopilot</option>
                        <option value="planner">planner</option>
                        <option value="webgpt">webgpt</option>
                        <option value="artist">artist</option>
                        <option value="agi">agi</option>
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
                {conversationTree.conversations[path[path.length - 1]] && conversationTree.conversations[path[path.length - 1]].map((message, index) =>
                    <div className={`message-${message.role}`} key={index}>
                        {functionsToRenderAsCode.includes(message.name) ? <CodeBlock code={message.content} /> : <DisplayJson data={message.content} />}
                        {message.function_call && <DisplayJson data={message.function_call} />}
                        {(conversationTree.subConversations[message.id] || []).map(subConversationId => {
                            return (
                                <div onClick={() => handleSubConversationClick(subConversationId)}>View thread</div>
                            );
                        })}
                    </div>
                )}
                {path[path.length - 1] === "root" && (
                    // get the first messages of all sub conversations of root
                    Object.keys(conversationTree.parents).map(subConversationId => {
                        const parent = conversationTree.parents[subConversationId] || "root";
                        const message = conversationTree.conversations[subConversationId]?.find(i => i.is_init !== true);
                        if (parent !== "root") {
                            console.log("not root", subConversationId, parent, message);
                            return null;
                        }
                        console.log({ subConversationId, message });
                        if (!message) {
                            return null;
                        }
                        return (
                            <div className={`message-${message.role}`} key={subConversationId} onClick={() => pushToPath(subConversationId)}>
                                <DisplayJson data={message.content} />
                            </div>
                        );
                    })
                )}
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
