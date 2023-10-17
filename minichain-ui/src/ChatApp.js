import React, { useState, useEffect, useMemo } from "react";
import { w3cwebsocket as W3CWebSocket } from "websocket";
import './ChatApp.css';
import ChatMessage from "./ChatMessage";
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import NewCell from "./NewCell";


const backend = 'localhost:8745';


function ChatHeader({ path, setPath, conversation, defaultAgentName, setDefaultAgentName, availableAgents, setShowInitMessages, showInitMessages, token }) {
    const sendCancelRequest = (conversationId) => {
        // Send a GET /cancel/{conversationId} request
        fetch(`http://localhost:8745/cancel/${conversationId}`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
    }

    return (
        <div className="header">
            <ArrowBackIcon
                style={{
                    position: "absolute",
                    left: "-30px",
                    top: "10px",
                }}
                onClick={() => {
                    if (path.length === 1) {
                        return;
                    }
                    setPath(prevPath => prevPath.slice(0, prevPath.length - 1));
                }} />
            <button onClick={() => {
                setPath([...path, "root"]);
            }}>Main</button>
            <button onClick={() => {
                // parent
                const parent = conversation.path[conversation.path.length - 3] || "root";
                setPath([...path, parent]);
            }}>Parent</button>
            <button onClick={() => {
                // Scroll to the last message using scrollIntoView
                const bottom = document.getElementById("bottom");
                bottom?.scrollIntoView({ behavior: "smooth" });
            }}>Down</button>
            <button onClick={() => {
                // Send a cancel message to the websocket
                sendCancelRequest(conversation.path[conversation.path.length - 1]);
            }}>Interrupt</button>
            <button onClick={() => setShowInitMessages(prev => !prev)}>{showInitMessages ? 'Hide full history' : 'Show full history'}</button>
            {conversation.path}
            {path[path.length - 1] === "root" && (
                <select value={defaultAgentName} onChange={e => setDefaultAgentName(e.target.value)} style={{
                    position: "absolute",
                    right: "10px",
                    top: "10px",
                    backgroundColor: "black",
                    color: "white",
                    padding: "5px",
                }}>
                    {availableAgents.map(agentName => <option key={agentName} value={agentName}>{agentName}</option>)}
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
                    {conversation.meta?.agent || defaultAgentName}
                </div>
            )}

        </div>
    );
}


function ChatApp() {
    const [token, setToken] = useState(null);
    const [tokenInput, setTokenInput] = useState(null);
    const [isValidated, setIsValidated] = useState(false);
    const [errorMessage, setErrorMessage] = useState(null);


    useEffect(() => {
        function handleMessage(event) {
            const message = event.data;
            if (message.token) {
                setToken(message.token);
            }
        }

        window.addEventListener('message', handleMessage);

        return () => {
            window.removeEventListener('message', handleMessage);
        };
    }, []);

    // move the token from the get params to the state
    useEffect(() => {
        const urlParams = new URLSearchParams(window.location.search);
        const token = urlParams.get('token');
        if (token) {
            setToken(token);
        }
    }, []);

    // validate the token
    useEffect(() => {
        if (!token) {
            return;
        }
        fetch(`http://${backend}/messages/root`, {headers: {'Authorization': `Bearer ${token}`}})
            .then(response => {
                if (!response.ok) {
                    // If the response is not ok, throw an error
                    throw new Error(`HTTP error! Status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                console.log(data)
                setIsValidated(true);
            })
            .catch(e => {
                console.error(e);
                setErrorMessage(e.message);
            });
    }, [token]);


    if (!isValidated) {
        return (
            <div className="main">
                <div style={{ margin: 'auto', marginTop: '40vh', width: "350px" }}>
                    Enter your token: <input type="text" value={tokenInput} onChange={e => setTokenInput(e.target.value)} />
                    <button onClick={() => {
                        setToken(tokenInput);
                    }
                    }>Submit</button>
                    {errorMessage && (
                        <div className="error-message">
                            {errorMessage}
                        </div>
                    )}
                </div>
            </div>
        );
    }
    console.log("token", token);


    return (
        <AuthorizedChatApp token={token} />
    );
}

function ErrorHeader({ errorMessage, setErrorMessage }) {
    if (!errorMessage) {
        return '';
    }
    return (
        <div className="error-header">
            <div className="error-message">
                {errorMessage}
            </div>
            <button onClick={() => setErrorMessage(null)}>X</button>
        </div>
    );
}


function AuthorizedChatApp({token}) {
    const [path, setPath] = useState(["root"]);
    const [messages, setMessages] = useState([]);
    const [userMessage, setUserMessage] = useState("");
    const [conversation, setConversation] = useState({
        "path": ["root"],
        "messages": [],
    });
    const [defaultAgentName, setDefaultAgentName] = useState("Programmer");
    const [availableAgents, setAvailableAgents] = useState([]);
    const [showInitMessages, setShowInitMessages] = useState(false);
    const [streamingState, setStreamingState] = useState({
        messages: {},
        sortedIds: []
    });
    const [errorMessage, setErrorMessage] = useState(null);


    // fetch the available agents
    useEffect(() => {
        fetch(`http://${backend}/agents`, {headers: {'Authorization': `Bearer ${token}`}})
            .then(response => response.json())
            .then(data => {
                setAvailableAgents(data);
            })
            .catch(e => {
                console.error(e);
            });
    }, [token]);

    // fetch the root conversation
    useEffect(() => {
        if (path[path.length - 1] !== "root") {
            return;
        }
        const url = `http://${backend}/byagent/${defaultAgentName}`;
        fetch(url, {headers: {'Authorization': `Bearer ${token}`}})
            .then(response => {
                if (!response.ok) {
                    // If the response is not ok, throw an error
                    throw new Error(`HTTP error! Status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                console.log("got conversation", data);
                setConversation(data);
                setMessages(data.messages || []);
                setStreamingState({
                    messages: {},
                    sortedIds: []
                });
            })
            .catch(e => {
                setErrorMessage(e.message);
            });
    }, [path, defaultAgentName, token]);


    // fetch the conversation
    useEffect(() => {
        // connect to a websocket
        // the websocket will send us a bunch of messages initially, then continue with chunks
        // of messages as they come in
        // we keep all but the last message in the `messages` state
        // and the last message in the `streamingState` state

        // fetch the conversation metadata
        if (path[path.length - 1] === "root") {
            return;
        }

        fetch(`http://${backend}/messages/${path[path.length - 1]}`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        })
            .then(response => response.json())
            .then(data => {
                console.log("got conversation", data);
                setConversation(data);
            })
            .catch(e => {
                console.error(e);
            });


        const client = new W3CWebSocket(`ws://${backend}/ws/${path[path.length - 1]}`);
        client.onopen = () => {
            console.log('WebSocket Client Connected');
            setMessages([]);
            setStreamingState({
                messages: {},
                sortedIds: []
            });
            // send token as first message
            client.send(token);
        };

        client.onmessage = (messageRaw) => {
            const message = JSON.parse(messageRaw.data);
            /**

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
            if (message.type === "set" && message.meta.duration !== undefined) {
                // this message has finished streaming
                // remove it from the streaming state and add it to messages
                setStreamingState(prev => {
                    const messages = { ...prev.messages };
                    delete messages[message.id];
                    const sortedIds = prev.sortedIds.filter(id => id !== message.id);
                    return {
                        sortedIds: sortedIds,
                        messages: messages
                    };
                });
                // add the message to the conversation or replace it if it exists already
                setMessages(prev => {
                    const newMessages = [...prev];
                    const existingMessageIndex = newMessages.findIndex(i => i.path[i.path.length - 1] === message.id);
                    if (existingMessageIndex !== -1) {
                        newMessages[existingMessageIndex] = message;
                    } else {
                        console.log("insert after", message.meta.insert_after);
                        const pos = newMessages.findIndex(i => i.path[i.path.length - 1] === message.meta.insert_after);
                        if (pos === -1) {
                            newMessages.push(message);
                        } else {
                            newMessages.splice(pos + 1, 0, message);
                        }
                    }
                    return newMessages;
                });
            } else if (message.type === "set" && message.meta.duration === undefined) {
                console.log("got initial message", message);
                // initializing a new stream of chunks for this message
                // add it to the streaming state
                setStreamingState(prev => {
                    const messages = { ...prev.messages };
                    messages[message.id] = message;
                    const sortedIds = prev.sortedIds;
                    if (!sortedIds.includes(message.id)) {
                        sortedIds.push(message.id);
                    }
                    return {
                        sortedIds: sortedIds,
                        messages: messages
                    };
                });
            } else if (message.type === "chunk") {
                setStreamingState(prev => {
                    const currentMessage = prev.messages[message.id];
                    if (!currentMessage) {
                        console.log("no current message", message, prev.messages);
                        return prev;
                    }
                    const newMessage = addDiffToMessage(currentMessage, { chat: message.diff });
                    const messages = { ...prev.messages };
                    messages[message.id] = newMessage;
                    return {
                        messages: messages,
                        sortedIds: prev.sortedIds
                    };
                });
            } else {
                console.error("Unknown message type", message);
            }
        };

        client.onclose = () => {
            console.log('WebSocket Client Closed');
        }
        client.onerror = (e) => {
            console.error('WebSocket error', e);
        }
        return () => {
            client.close();
        }
    }, [path, token]);


    const handleSubConversationClick = (subConversationId) => {
        if (!subConversationId) {
            // just refresh this conversation
            setPath([...path]);
        }
        if (subConversationId) {
            console.log("setting path to", [...path, subConversationId]);
            setPath([...path, subConversationId]);
        }
    };

    const runCodeAfterMessage = (message) => async (code) => {
        // send the code as a POST request to /run/
        await fetch(`http://localhost:8745/run/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                code: code,
                type: message.chat.function_call.arguments.type,
                insert_after: message.path
            }),
        });
        // update path to refresh the conversation
        // setPath([...path]);
    }

    const saveCodeInMessage = (message) => async (code) => {
        // send the code as a PUT request to /chat/
        console.log("saving code in message", message);
        await fetch(`http://localhost:8745/chat/${message.path[message.path.length - 1]}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                function_call: {
                    name: message.chat.function_call.name,
                    arguments: { ...message.chat.function_call.arguments, code: code },
                },
            }),
        });
        // update path to refresh the conversation
        setPath([...path]);
    }

    function forkFromMessage(path) {
        // Send GET request to /fork/{path} to fork a conversation
        const pathString = path.join('/');
        fetch(`http://localhost:8745/fork/${pathString}`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
        }).then(response => response.json())
            .then(data => {
                setPath(data.path);
            });
    }

    function createNewCell(code) {
        fetch(`http://${backend}/cell/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                code: code,
                insert_after: messages[messages.length - 1].path,
            }),
        });
    }

    function postMessage() {
        fetch(`http://${backend}/message/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                query: userMessage,
                response_to: conversation.path[conversation.path.length - 1],
                agent: conversation.meta.agent || defaultAgentName,
            }),
        }).then(response => response.json())
            .then(data => {
                setPath([...path, data.path[data.path.length - 1]]);
            });
        setUserMessage("");
    }



    return (
        <div className="main">
            <ChatHeader
                path={path}
                setPath={setPath}
                conversation={conversation}
                availableAgents={availableAgents}
                defaultAgentName={defaultAgentName}
                setDefaultAgentName={setDefaultAgentName}
                setShowInitMessages={setShowInitMessages}
                showInitMessages={showInitMessages}
                token={token}
            />
            <div style={{ height: "50px" }}></div>
            <ErrorHeader errorMessage={errorMessage} setErrorMessage={setErrorMessage} />
            <div className="chat">
                {(messages).map((message, i) => {
                    if (message.meta.deleted || (message.meta.is_initial && !showInitMessages))
                        return '';
                    return (
                        <ChatMessage
                            key={message.path[message.path.length - 1]}
                            message={message}
                            handleSubConversationClick={handleSubConversationClick}
                            runCodeAfterMessage={runCodeAfterMessage}
                            saveCodeInMessage={saveCodeInMessage}
                            forkFromMessage={forkFromMessage}
                            token={token}
                        />
                    )
                })}
                {(streamingState.sortedIds).map(id => streamingState.messages[id]).map((message, i) => {
                    if (message.meta.deleted || (message.meta.is_initial && !showInitMessages))
                        return '';
                    return (
                        <ChatMessage
                            key={message.path[message.path.length - 1]}
                            message={message}
                            handleSubConversationClick={handleSubConversationClick}
                            runCodeAfterMessage={runCodeAfterMessage}
                            saveCodeInMessage={saveCodeInMessage}
                            forkFromMessage={forkFromMessage}
                            token={token}
                        />
                    )
                })}
                {conversation.meta?.agent === 'Programmer' && (
                    <NewCell onRun={createNewCell} />
                )}
                <div id="bottom"></div> {/* this is used to scroll to the bottom when a new message is added */}
            </div>
            <div className="spacer"></div>
            <div className="input-area">
                <textarea className="user-input" value={userMessage} onChange={e => setUserMessage(e.target.value)}></textarea>
                <button className="send-button" onClick={postMessage}>Send</button>
            </div>
        </div>
    );
}


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


export default ChatApp;