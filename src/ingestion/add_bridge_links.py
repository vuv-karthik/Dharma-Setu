import os
import json
import pickle
import logging
import time
from typing import List, Dict
from dotenv import load_dotenv
import networkx as nx
from networkx.readwrite import json_graph
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

# Configuration
GRAPH_PICKLE_PATH = "data/processed/legal_graph.gpickle"
GRAPH_JSON_PATH = "data/processed/legal_graph.json"
MODEL_NAME = "gemini-2.0-flash-exp"

def get_llm():
    """Initialize Gemini model."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not found")
    
    return ChatGoogleGenerativeAI(
        model=MODEL_NAME,
        google_api_key=api_key,
        temperature=0.0
    )

def identify_regime(node_label: str) -> str:
    """Identify if a node is Legacy (IPC) or Current (BNS)."""
    label_upper = node_label.upper()
    if "IPC" in label_upper or "PENAL CODE" in label_upper:
        return "Legacy"
    if "BNS" in label_upper or "BHARATIYA" in label_upper:
        return "Current"
    return "Unknown"

def find_equivalents(llm, ipc_nodes: List[str], bns_nodes: List[str]) -> Dict[str, str]:
    """
    Ask LLM to map IPC nodes to BNS nodes.
    Returns a dict: {ipc_node_label: bns_node_label}
    """
    if not ipc_nodes or not bns_nodes:
        return {}
    
    # We pass the lists to the LLM and ask it to match them
    # This assumes the node labels are descriptive enough (e.g. "Section 302 IPC")
    
    system_prompt = """You are a legal expert. Map the provided IPC (Old) sections to their BNS (New) equivalents.
    
**Instructions:**
1. I will provide a list of IPC Nodes and a list of BNS Nodes from my database.
2. For each IPC Node, find the semantic equivalent in the BNS Node list.
3. Return a JSON object where keys are IPC Node names and values are BNS Node names.
4. If no exact match exists in the BNS list, map to NULL.
5. STRICTLY only use the node names provided in the lists.

**Format:**
```json
{
  "Section 302 IPC": "Section 103 BNS",
  "Section 420 IPC": "Section 318 BNS"
}
```
"""

    human_message = f"""
**IPC Nodes (Legacy):**
{json.dumps(ipc_nodes, indent=2)}

**BNS Nodes (Current):**
{json.dumps(bns_nodes, indent=2)}

**Task:** return the mapping JSON.
"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_message)
    ]

    try:
        response = llm.invoke(messages)
        content = response.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        mapping = json.loads(content)
        return mapping
    except Exception as e:
        logger.error(f"Error in LLM mapping: {e}")
        return {}

def add_bridge_links():
    logger.info("Starting Bridge Link Analysis...")
    
    # Load Graph
    if not os.path.exists(GRAPH_PICKLE_PATH):
        logger.error("Graph file not found!")
        return

    logger.info(f"Loading graph from {GRAPH_PICKLE_PATH}...")
    with open(GRAPH_PICKLE_PATH, 'rb') as f:
        G = pickle.load(f)
    
    # Identify Nodes
    ipc_nodes = []
    bns_nodes = []
    
    for node in G.nodes():
        regime = identify_regime(node)
        G.nodes[node]['regime'] = regime # Update metadata
        
        if regime == "Legacy":
            ipc_nodes.append(node)
        elif regime == "Current":
            bns_nodes.append(node)
            
    logger.info(f"Identified {len(ipc_nodes)} IPC nodes and {len(bns_nodes)} BNS nodes.")
    
    if not ipc_nodes:
        logger.warning("No IPC nodes found. Checking heuristic...")
        # Fallback: Maybe labels don't have "IPC". 
        # For now, let's assume the graph has correct labels from ingestion.
        # If not, we might need to inspect the graph structure.
        pass

    # Batch Process Mapping
    # We'll send all candidates to LLM if the lists are small (<100). 
    # If large, we should chunk. Assuming reasonably small for this demo.
    
    llm = get_llm()
    
    # Process in chunks of 20 IPC nodes to avoid context limits
    chunk_size = 20
    new_edges_count = 0
    
    for i in range(0, len(ipc_nodes), chunk_size):
        chunk_ipc = ipc_nodes[i:i+chunk_size]
        logger.info(f"Processing chunk {i//chunk_size + 1}: {len(chunk_ipc)} nodes...")
        
        mapping = find_equivalents(llm, chunk_ipc, bns_nodes)
        
        for ipc_node, bns_node in mapping.items():
            if bns_node and bns_node in G.nodes():
                if not G.has_edge(ipc_node, bns_node):
                    G.add_edge(ipc_node, bns_node, relation="EQUIVALENT_TO", label="Equivalent To")
                    
                    # Also add reverse edge for bidirectional traversal?
                    # Directed graph: IPC -> BNS makes sense for "Migration".
                    # But BNS -> IPC is also useful for "History".
                    # Let's add both or just one? "EQUIVALENT_TO" implies symmetry.
                    # Let's add undirected semantic, but NetworkX DiGraph needs explicit edges.
                    G.add_edge(bns_node, ipc_node, relation="EQUIVALENT_TO", label="Legacy Equivalent")
                    
                    logger.info(f"  Linked: {ipc_node} <--> {bns_node}")
                    new_edges_count += 1
            else:
                if bns_node:
                    logger.debug(f"  Skipped: {bns_node} not in graph or null")

    logger.info(f"Added {new_edges_count} new bridge edges.")
    
    # Save Graph
    logger.info("Saving updated graph...")
    with open(GRAPH_PICKLE_PATH, 'wb') as f:
        pickle.dump(G, f)
        
    graph_data = json_graph.node_link_data(G)
    with open(GRAPH_JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(graph_data, f, indent=2, ensure_ascii=False)
        
    logger.info("✅ Bridge links implementation complete!")

if __name__ == "__main__":
    add_bridge_links()
