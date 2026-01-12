"""
Graph-based Context Expansion Agent

This module implements intelligent context expansion using the legal knowledge graph.
It decides when to traverse the graph to find related legal provisions.
"""

import os
import json
import pickle
import logging
from typing import List, Dict, Tuple
from dotenv import load_dotenv

import networkx as nx
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

# Configuration
GRAPH_PICKLE_PATH = "data/processed/legal_graph.gpickle"
MODEL_NAME = "gemini-2.0-flash-exp"

class GraphContextExpander:
    """Manages graph-based context expansion for legal queries."""
    
    def __init__(self):
        """Initialize the expander with the knowledge graph and LLM."""
        self.graph = self._load_graph()
        self.llm = self._init_llm()
        
    def _load_graph(self) -> nx.DiGraph:
        """Load the legal knowledge graph."""
        if not os.path.exists(GRAPH_PICKLE_PATH):
            raise FileNotFoundError(f"Graph not found at {GRAPH_PICKLE_PATH}. Run graph_constructor.py first.")
        
        logger.info(f"Loading knowledge graph from {GRAPH_PICKLE_PATH}...")
        with open(GRAPH_PICKLE_PATH, 'rb') as f:
            graph = pickle.load(f)
        
        logger.info(f"Graph loaded: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")
        return graph
    
    def _init_llm(self) -> ChatGoogleGenerativeAI:
        """Initialize Gemini model for decision making."""
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables")
        
        return ChatGoogleGenerativeAI(
            model=MODEL_NAME,
            google_api_key=api_key,
            temperature=0.0,
            convert_system_message_to_human=True
        )
    
    def should_expand_context(self, query: str, retrieved_docs: List[Dict]) -> Tuple[bool, str]:
        """
        Decision node: Determine if context expansion is needed.
        
        Args:
            query: User's legal query
            retrieved_docs: Documents retrieved from vector search
            
        Returns:
            Tuple of (should_expand: bool, reasoning: str)
        """
        # Format retrieved documents
        docs_summary = "\n".join([
            f"- {doc.get('source_doc', 'Unknown')} (Page {doc.get('page_number', '?')}): {doc.get('text', '')[:200]}..."
            for doc in retrieved_docs[:5]  # Limit to top 5 for token efficiency
        ])
        
        decision_prompt = f"""You are a legal research assistant. Analyze whether the retrieved documents fully answer the query or if additional related provisions should be consulted.

**User Query:** {query}

**Retrieved Documents:**
{docs_summary}

**Your Task:**
Determine if these documents reference other sections, exceptions, or related provisions that are NOT in the current retrieval results but might be crucial for a complete answer.

**Answer with ONLY:**
- "YES" if additional context is needed (e.g., documents mention other sections, exceptions, or definitions not retrieved)
- "NO" if the current documents are sufficient

**Examples:**
- If a document mentions "except as provided in Section 96" but Section 96 is not retrieved → YES
- If a document references "as defined in Section 2" but Section 2 is not retrieved → YES  
- If all mentioned sections are already in the results → NO

**Your Answer (YES or NO):**"""

        try:
            messages = [
                SystemMessage(content="You are a precise legal analyst. Answer only YES or NO."),
                HumanMessage(content=decision_prompt)
            ]
            
            response = self.llm.invoke(messages)
            answer = response.content.strip().upper()
            
            should_expand = "YES" in answer
            
            logger.info(f"Context expansion decision: {answer}")
            return should_expand, answer
            
        except Exception as e:
            logger.error(f"Error in decision making: {e}")
            return False, f"Error: {e}"
    
    def expand_context(self, retrieved_docs: List[Dict], max_hops: int = 1) -> List[str]:
        """
        Expand context by traversing the knowledge graph.
        
        Args:
            retrieved_docs: Initial retrieved documents
            max_hops: Maximum number of graph hops (default: 1 for direct neighbors)
            
        Returns:
            List of additional entity names to retrieve
        """
        # Extract entity names from retrieved documents
        seed_entities = set()
        for doc in retrieved_docs:
            text = doc.get('text', '')
            # Simple entity extraction: look for "Section XXX", "Article XXX", etc.
            import re
            sections = re.findall(r'Section\s+\d+[A-Z]?', text, re.IGNORECASE)
            articles = re.findall(r'Article\s+\d+[A-Z]?', text, re.IGNORECASE)
            seed_entities.update(sections + articles)
        
        logger.info(f"Seed entities from retrieved docs: {seed_entities}")
        
        # Find neighbors in the graph
        expanded_entities = set()
        for entity in seed_entities:
            if entity in self.graph:
                # Get all neighbors (both incoming and outgoing edges)
                neighbors = set(self.graph.predecessors(entity)) | set(self.graph.successors(entity))
                expanded_entities.update(neighbors)
                
                logger.info(f"  {entity} → {len(neighbors)} neighbors")
        
        # Remove entities we already have
        new_entities = expanded_entities - seed_entities
        
        logger.info(f"Found {len(new_entities)} new entities to retrieve")
        return list(new_entities)
    
    def get_entity_relationships(self, entity: str) -> List[Dict]:
        """
        Get all relationships for a specific entity.
        
        Args:
            entity: Entity name (e.g., "Section 302")
            
        Returns:
            List of relationship dictionaries
        """
        if entity not in self.graph:
            return []
        
        relationships = []
        
        # Outgoing edges (entity → other)
        for target in self.graph.successors(entity):
            edge_data = self.graph.get_edge_data(entity, target)
            target_meta = self.graph.nodes[target]
            relationships.append({
                "subject": entity,
                "predicate": edge_data.get('relation', 'UNKNOWN'),
                "object": target,
                "direction": "outgoing",
                "other_metadata": target_meta
            })
        
        # Incoming edges (other → entity)
        for source in self.graph.predecessors(entity):
            edge_data = self.graph.get_edge_data(source, entity)
            source_meta = self.graph.nodes[source]
            relationships.append({
                "subject": source,
                "predicate": edge_data.get('relation', 'UNKNOWN'),
                "object": entity,
                "direction": "incoming",
                "other_metadata": source_meta
            })
        
        return relationships


def demo_context_expansion():
    """Demo function to test the context expansion logic."""
    expander = GraphContextExpander()
    
    # Simulated query and retrieval results
    query = "What is the punishment for murder under BNS?"
    
    retrieved_docs = [
        {
            "text": "Section 302 prescribes punishment for murder. The punishment is death or life imprisonment, and also liable to fine. This section applies except in cases covered by Section 300.",
            "source_doc": "Bharatiya_Nyaya_Sanhita_2023",
            "page_number": 45
        }
    ]
    
    logger.info(f"\n{'='*70}")
    logger.info(f"DEMO: Context Expansion")
    logger.info(f"{'='*70}")
    logger.info(f"Query: {query}\n")
    
    # Step 1: Decision
    should_expand, reasoning = expander.should_expand_context(query, retrieved_docs)
    logger.info(f"Decision: {'EXPAND' if should_expand else 'NO EXPANSION'}")
    logger.info(f"Reasoning: {reasoning}\n")
    
    # Step 2: Expansion (if needed)
    if should_expand:
        new_entities = expander.expand_context(retrieved_docs)
        logger.info(f"New entities to retrieve: {new_entities}\n")
        
        # Step 3: Show relationships
        for entity in list(new_entities)[:3]:  # Show first 3
            rels = expander.get_entity_relationships(entity)
            if rels:
                logger.info(f"Relationships for {entity}:")
                for rel in rels[:5]:  # Show first 5 relationships
                    logger.info(f"  {rel['subject']} --[{rel['predicate']}]--> {rel['object']}")
    
    logger.info(f"{'='*70}\n")


if __name__ == "__main__":
    demo_context_expansion()
