import os
import json
import time
import pickle
import logging
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
PARSED_DATA_PATH = "data/processed/parsed_elements.json"
GRAPH_PICKLE_PATH = "data/processed/legal_graph.gpickle"
GRAPH_JSON_PATH = "data/processed/legal_graph.json"
MODEL_NAME = "gemini-2.0-flash-exp"
BATCH_SIZE = 20

# Strict predicates
ALLOWED_PREDICATES = ["DEFINES", "PUNISHES", "REFERENCES", "PART_OF", "EXCEPTION_TO"]

SYSTEM_PROMPT = f"""You are a legal knowledge extraction AI. Your task is to extract structured legal relationships from text.

**Instructions:**
1. Read the provided legal text carefully.
2. Extract relationships in the form of triples: (Subject, Predicate, Object)
3. Use ONLY these predicates: {', '.join(ALLOWED_PREDICATES)}
4. Return a JSON array of objects with this exact structure: {{"subject": "...", "predicate": "...", "object": "..."}}

**Predicate Definitions:**
- DEFINES: Subject defines or establishes the meaning of Object (e.g., "Section 2" DEFINES "Theft")
- PUNISHES: Subject prescribes punishment for Object (e.g., "Section 302" PUNISHES "Murder")
- REFERENCES: Subject refers to or cites Object (e.g., "Section 34" REFERENCES "Section 120B")
- PART_OF: Subject is a component of Object (e.g., "Article 14" PART_OF "Part III")
- EXCEPTION_TO: Subject is an exception to Object (e.g., "Section 96" EXCEPTION_TO "Section 300")

**Examples:**
Input: "Section 378 defines theft as dishonest misappropriation of property."
Output: [{{"subject": "Section 378", "predicate": "DEFINES", "object": "Theft"}}]

Input: "Section 302 prescribes punishment for murder with death or life imprisonment."
Output: [{{"subject": "Section 302", "predicate": "PUNISHES", "object": "Murder"}}]

**Important:**
- Extract multiple triples if the text contains multiple relationships
- Be precise with entity names (use exact section numbers, article numbers, etc.)
- If no clear relationships exist, return an empty array []
- Always return valid JSON
"""

def get_llm():
    """Initialize Gemini 2.5 Flash model."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not found in environment variables")
    
    return ChatGoogleGenerativeAI(
        model=MODEL_NAME,
        google_api_key=api_key,
        temperature=0.0,  # Deterministic for extraction
        convert_system_message_to_human=True
    )

def extract_triples_from_batch(llm, texts: List[str]) -> List[Dict]:
    """Extract legal triples from a batch of texts using LLM."""
    # Combine texts for batch processing
    combined_text = "\n\n---\n\n".join([f"Text {i+1}:\n{text}" for i, text in enumerate(texts)])
    
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"Extract legal triples from the following texts:\n\n{combined_text}")
    ]
    
    try:
        response = llm.invoke(messages)
        content = response.content
        
        # Try to parse JSON from response
        # Sometimes LLM wraps JSON in markdown code blocks
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        triples = json.loads(content)
        
        # Validate predicates
        valid_triples = []
        for triple in triples:
            if triple.get("predicate") in ALLOWED_PREDICATES:
                valid_triples.append(triple)
            else:
                logger.warning(f"Invalid predicate '{triple.get('predicate')}' - skipping triple")
        
        return valid_triples
    
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON from LLM response: {e}")
        logger.debug(f"Response content: {content}")
        return []
    except Exception as e:
        logger.error(f"Error extracting triples: {e}")
        return []

def build_knowledge_graph():
    """Main function to build the legal knowledge graph."""
    logger.info("Starting knowledge graph construction...")
    
    # Load parsed data
    if not os.path.exists(PARSED_DATA_PATH):
        logger.error(f"Parsed data not found at {PARSED_DATA_PATH}")
        return
    
    logger.info(f"Loading data from {PARSED_DATA_PATH}...")
    with open(PARSED_DATA_PATH, 'r', encoding='utf-8') as f:
        elements = json.load(f)
    
    logger.info(f"Loaded {len(elements)} elements")
    
    # Initialize LLM
    llm = get_llm()
    
    # Initialize graph
    G = nx.DiGraph()
    
    # Process in batches
    all_triples = []
    total_batches = (len(elements) + BATCH_SIZE - 1) // BATCH_SIZE
    
    for i in range(0, len(elements), BATCH_SIZE):
        batch_num = (i // BATCH_SIZE) + 1
        batch = elements[i:i + BATCH_SIZE]
        
        # Extract texts
        texts = []
        for el in batch:
            text = el.get("text", "").strip()
            if len(text) > 50:  # Only process substantial text
                texts.append(text[:1000])  # Limit to first 1000 chars to save tokens
        
        if not texts:
            continue
        
        logger.info(f"Processing batch {batch_num}/{total_batches} ({len(texts)} texts)...")
        
        # Extract triples
        triples = extract_triples_from_batch(llm, texts)
        all_triples.extend(triples)
        
        logger.info(f"  Extracted {len(triples)} triples from batch {batch_num}")
        
        # Add to graph
        for triple in triples:
            subject = triple["subject"]
            predicate = triple["predicate"]
            obj = triple["object"]
            
            # Add nodes
            G.add_node(subject, type="entity")
            G.add_node(obj, type="entity")
            
            # Add edge with predicate as attribute
            G.add_edge(subject, obj, relation=predicate)
        
        # Rate limiting
        if i + BATCH_SIZE < len(elements):
            time.sleep(2)  # 2 second delay between batches
    
    logger.info(f"\n{'='*70}")
    logger.info(f"Graph construction complete!")
    logger.info(f"  Total triples extracted: {len(all_triples)}")
    logger.info(f"  Graph nodes: {G.number_of_nodes()}")
    logger.info(f"  Graph edges: {G.number_of_edges()}")
    logger.info(f"{'='*70}\n")
    
    # Save graph as pickle
    logger.info(f"Saving graph to {GRAPH_PICKLE_PATH}...")
    os.makedirs(os.path.dirname(GRAPH_PICKLE_PATH), exist_ok=True)
    with open(GRAPH_PICKLE_PATH, 'wb') as f:
        pickle.dump(G, f)
    
    # Save graph as JSON for inspection
    logger.info(f"Saving graph to {GRAPH_JSON_PATH}...")
    graph_data = json_graph.node_link_data(G)
    with open(GRAPH_JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(graph_data, f, indent=2, ensure_ascii=False)
    
    logger.info("Knowledge graph saved successfully!")
    
    # Print sample triples
    logger.info("\nSample triples:")
    for i, triple in enumerate(all_triples[:10], 1):
        logger.info(f"  {i}. {triple['subject']} --[{triple['predicate']}]--> {triple['object']}")
    
    return G

if __name__ == "__main__":
    build_knowledge_graph()
