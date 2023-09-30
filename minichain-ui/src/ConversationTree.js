import React from "react";
import { ForceGraph2D } from "react-force-graph";

function ConversationTree({ convTree, path, pushToPath, root='root' }) {
    const { messages, childrenOf } = convTree;

    const nodes = Object.keys(messages).map(id => ({ id, ...messages[id] }));
    nodes.push(...Object.values(childrenOf).flat());

    const nodeMap = {};
    nodes.forEach(node => {
        nodeMap[node.id] = {"id": node.id};
    });

    const links = [];
    for (let parent in childrenOf) {
        childrenOf[parent].forEach(child => {
            links.push({ source: nodeMap[parent], target: nodeMap[child] });
        });
    }

    return (
        <ForceGraph2D
            graphData={{ "nodes": Object.values(nodeMap) , links }}
            nodeLabel="id"
            onNodeClick={node => pushToPath(node.id)}
            onNodeHover={node => {
                if (node) {
                    // Display the ChatMessage component here
                    // This is just a placeholder and you'd replace it with your ChatMessage component
                    console.log(`Hovered over ${node.id}: ${node.content}`);
                }
            }}
        />
    );
}


export default ConversationTree;