"""
Enhanced Test Client for Dharma-Setu Legal RAG API

Demonstrates UI-ready features: UUIDs, graph data, and tooltips.
"""

import requests
import json
from typing import Dict

API_BASE_URL = "http://localhost:8000"


def test_health():
    """Test the health check endpoint."""
    print("\n" + "="*70)
    print("Testing Health Endpoint")
    print("="*70)
    
    response = requests.get(f"{API_BASE_URL}/health")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.json()


def ask_question(query: str, include_graph: bool = True) -> Dict:
    """
    Ask a legal question to the API.
    
    Args:
        query: Legal question
        include_graph: Whether to include graph visualization data
        
    Returns:
        API response dictionary
    """
    print("\n" + "="*70)
    print(f"Query: {query}")
    print("="*70)
    
    payload = {
        "query": query,
        "include_graph_data": include_graph
    }
    
    response = requests.post(
        f"{API_BASE_URL}/ask",
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        result = response.json()
        
        print(f"\n📝 ANSWER:")
        print("-" * 70)
        print(result["answer"])
        
        print(f"\n📚 CITATIONS ({len(result['citations'])}):")
        print("-" * 70)
        for i, citation in enumerate(result["citations"], 1):
            print(f"\n{i}. [{citation['uuid'][:8]}...] {citation.get('entity_name', 'N/A')}")
            print(f"   Source: {citation['source_doc']} (Page {citation['page_number']})")
            print(f"   Type: {citation['law_type']} | Score: {citation['score']:.4f}")
            print(f"   Summary: {citation['summary'][:100]}...")
        
        # Display graph data if present
        if result.get("graph_data"):
            graph = result["graph_data"]
            print(f"\n🕸️  GRAPH DATA:")
            print("-" * 70)
            print(f"Stats: {json.dumps(graph['stats'], indent=2)}")
            
            print(f"\nNodes ({len(graph['nodes'])}):")
            for node in graph['nodes'][:5]:  # Show first 5
                cited_marker = "📌" if node.get('citation_uuid') else "  "
                print(f"  {cited_marker} {node['label']} ({node['type']})")
                if node.get('metadata', {}).get('tooltip'):
                    print(f"     Tooltip: {node['metadata']['tooltip'][:80]}...")
            
            if len(graph['nodes']) > 5:
                print(f"  ... and {len(graph['nodes']) - 5} more nodes")
            
            print(f"\nEdges ({len(graph['edges'])}):")
            for edge in graph['edges'][:5]:  # Show first 5
                print(f"  {edge['source']} --[{edge['relation']}]--> {edge['target']}")
            
            if len(graph['edges']) > 5:
                print(f"  ... and {len(graph['edges']) - 5} more edges")
        
        print(f"\n📊 METADATA:")
        print("-" * 70)
        for key, value in result["metadata"].items():
            print(f"  {key}: {value}")
        
        return result
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text)
        return {}


def demonstrate_ui_features(result: Dict):
    """
    Demonstrate how UI can use the enhanced data.
    
    Args:
        result: API response
    """
    print("\n" + "="*70)
    print("UI INTEGRATION EXAMPLES")
    print("="*70)
    
    # Example 1: Citation with UUID
    if result.get("citations"):
        citation = result["citations"][0]
        print("\n1. Citation Card Component:")
        print(f"""
        <CitationCard
          uuid="{citation['uuid']}"
          entity="{citation.get('entity_name', 'N/A')}"
          source="{citation['source_doc']}"
          page={citation['page_number']}
          score={citation['score']:.2f}
          tooltip="{citation['summary']}"
        />
        """)
    
    # Example 2: Graph Node with Tooltip
    if result.get("graph_data") and result["graph_data"]["nodes"]:
        node = result["graph_data"]["nodes"][0]
        print("\n2. Graph Node with Hover Tooltip:")
        print(f"""
        <GraphNode
          id="{node['id']}"
          label="{node['label']}"
          type="{node['type']}"
          citationUuid="{node.get('citation_uuid', 'null')}"
          tooltip={{{{
            text: "{node['metadata'].get('tooltip', 'N/A').replace(chr(10), ' ')}",
            relationshipCount: {node['metadata'].get('relationship_count', 0)}
          }}}}
        />
        """)
    
    # Example 3: Linking Citations to Graph
    print("\n3. Citation-to-Graph Linking:")
    cited_nodes = [
        n for n in result.get("graph_data", {}).get("nodes", [])
        if n.get("citation_uuid")
    ]
    print(f"   Found {len(cited_nodes)} nodes linked to citations")
    for node in cited_nodes[:3]:
        print(f"   - {node['label']} → Citation UUID: {node['citation_uuid'][:8]}...")


def main():
    """Run enhanced test queries."""
    print("\n" + "#"*70)
    print("# Dharma-Setu Legal RAG API - Enhanced Test Client")
    print("# Demonstrating UI-Ready Features")
    print("#"*70)
    
    # Test health
    health = test_health()
    
    if health.get("status") != "healthy":
        print("\n❌ API is not healthy. Exiting.")
        return
    
    # Test query with full features
    query = "What is the punishment for theft under BNS?"
    
    try:
        result = ask_question(query, include_graph=True)
        
        if result:
            print("\n✅ Query processed successfully")
            demonstrate_ui_features(result)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
    
    print("\n" + "="*70)
    print("Test complete! Check the output above for UI integration examples.")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
