"""
FastAPI Backend for Legal RAG System

Exposes the LangGraph orchestrator as a REST API with structured responses.
Enhanced with UI-ready features: UUIDs, graph metadata, and hover tooltips.
"""

import os
import sys
import logging
import uuid
from typing import Dict, List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# Add src to path
sys.path.append(os.getcwd())
from src.agents.orchestrator import LegalRAGOrchestrator
from src.agents.auditor import AuditAgent

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
orchestrator: Optional[LegalRAGOrchestrator] = None
audit_agent: Optional[AuditAgent] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle - initialize services on startup."""
    global orchestrator, audit_agent
    logger.info("Initializing Services...")
    try:
        orchestrator = LegalRAGOrchestrator()
        audit_agent = AuditAgent()
        logger.info("✅ Orchestrator and Audit Agent initialized successfully")
        yield
    except Exception as e:
        logger.error(f"❌ Failed to initialize services: {e}")
        raise
    finally:
        logger.info("Shutting down...")


# Initialize FastAPI app
app = FastAPI(
    title="Dharma-Setu Legal RAG API",
    description="Advanced Legal Research Assistant with Graph-Enhanced Retrieval",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response Models
class DraftRequest(BaseModel):
    facts: str = Field(..., description="Facts of the case")
    language: str = Field(
        default="English",
        description="Target language for the memo"
    )
    input_language: str = Field(
        default="English",
        description="Language of the input facts"
    )


class QueryRequest(BaseModel):
    """Request model for legal queries."""
    query: str = Field(..., description="Legal question to ask", min_length=5)
    include_graph_data: bool = Field(
        default=True,
        description="Whether to include graph visualization data in response"
    )
    language: str = Field(
        default="English",
        description="Target language for the answer (e.g., Hindi, Telugu, Tamil)"
    )
    input_language: str = Field(
        default="English",
        description="Language of the input query (English or Native)"
    )


class Citation(BaseModel):
    """Enhanced citation model with UUID and metadata."""
    uuid: str = Field(..., description="Unique identifier for this citation")
    text: str = Field(..., description="Full text of the cited provision")
    source_doc: str = Field(..., description="Source document name")
    page_number: int = Field(..., description="Page number in source document")
    law_type: str = Field(..., description="Type of law (Constitutional/Statute)")
    score: float = Field(..., description="Relevance score from vector search")
    entity_name: Optional[str] = Field(None, description="Extracted entity name (e.g., 'Section 302')")
    summary: str = Field(..., description="Short summary for UI tooltips")


class GraphNode(BaseModel):
    """Enhanced graph node model with metadata for UI."""
    id: str = Field(..., description="Node identifier")
    label: str = Field(..., description="Display label")
    type: str = Field(default="entity", description="Node type")
    citation_uuid: Optional[str] = Field(None, description="UUID of related citation if applicable")
    metadata: Dict = Field(
        default_factory=dict,
        description="Additional metadata including hover tooltip text"
    )


class GraphEdge(BaseModel):
    """Graph edge model."""
    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    relation: str = Field(..., description="Relationship type (predicate)")
    label: Optional[str] = Field(None, description="Display label for edge")


class GraphData(BaseModel):
    """Graph visualization data."""
    nodes: List[GraphNode] = Field(..., description="Graph nodes with metadata")
    edges: List[GraphEdge] = Field(..., description="Graph edges")
    stats: Dict = Field(
        default_factory=dict,
        description="Graph statistics for UI display"
    )


class QueryResponse(BaseModel):
    """Enhanced response model for legal queries."""
    answer: str = Field(..., description="Comprehensive legal answer")
    citations: List[Citation] = Field(..., description="Citations with UUIDs and metadata")
    metadata: Dict = Field(..., description="Query execution metadata")
    graph_data: Optional[GraphData] = Field(
        None,
        description="Graph visualization data with linked citations"
    )


# API Endpoints
@app.post("/draft")
async def draft_legal_memo(request: DraftRequest):
    """
    Generate a formal Legal Memo (Written Submission) based on facts.
    """
    logger.info(f"Drafting memo for: {request.facts[:50]}...")
    
    if orchestrator is None:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    try:
        # Execute the Drafter pipeline
        result = orchestrator.draft(request.facts, language=request.language, input_language=request.input_language)
        
        # Generate UUIDs and format citations based on retrieved sources
        citations = []
        citation_map = {}
        
        for src in result["sources"]:
            citation_uuid = str(uuid.uuid4())
            extracted_entities = _extract_entities_from_text(src["text"], orchestrator)
            primary_entity_name = extracted_entities[0] if extracted_entities else None
            summary = _generate_summary(src["text"])
            
            citation = Citation(
                uuid=citation_uuid,
                text=src["text"],
                source_doc=src["source_doc"],
                page_number=src["page_number"],
                law_type=src["law_type"],
                score=src["score"],
                entity_name=primary_entity_name,
                summary=summary
            )
            citations.append(citation)
            for ent in extracted_entities:
                citation_map[ent] = citation_uuid

        return {
            "answer": result["answer"],
            "citations": citations, 
            "graph_data": None # Drafter doesn't return graph viz yet
        }
    except Exception as e:
        logger.error(f"Draft error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def root():
    """Root endpoint - API health check."""
    return {
        "service": "Dharma-Setu Legal RAG API",
        "status": "operational",
        "version": "1.0.0",
        "endpoints": {
            "ask": "/ask - POST - Submit legal queries",
            "health": "/health - GET - Health check",
            "docs": "/docs - GET - API documentation"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    if orchestrator is None:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    return {
        "status": "healthy",
        "orchestrator": "initialized",
        "graph_loaded": orchestrator.graph_expander.graph is not None,
        "graph_stats": {
            "nodes": orchestrator.graph_expander.graph.number_of_nodes(),
            "edges": orchestrator.graph_expander.graph.number_of_edges()
        }
    }


@app.post("/ask", response_model=QueryResponse)
async def ask_legal_question(request: QueryRequest):
    """
    Submit a legal query and get a comprehensive answer with UI-ready data.
    
    This endpoint:
    1. Retrieves relevant documents from the vector database
    2. Expands context using the knowledge graph
    3. Generates a comprehensive answer with citations
    4. Assigns UUIDs to each citation
    5. Builds graph visualization data with linked citations
    
    Args:
        request: QueryRequest with the legal question
        
    Returns:
        QueryResponse with answer, citations (with UUIDs), and graph data
    """
    if orchestrator is None:
        raise HTTPException(
            status_code=503,
            detail="Service not ready. Orchestrator not initialized."
        )
    
    logger.info(f"Received query: {request.query}")
    
    try:
        # Execute the RAG pipeline
        result = orchestrator.query(request.query, language=request.language, input_language=request.input_language)
        
        # Generate UUIDs and format citations
        citations = []
        citation_map = {}  # Map entity names to UUIDs
        
        for src in result["sources"]:
            citation_uuid = str(uuid.uuid4())
            
            # Extract entity entities from text
            # We take the first one found as the primary entity for the citation, 
            # but mapping all found entities to this citation for graph linking
            extracted_entities = _extract_entities_from_text(src["text"], orchestrator)
            primary_entity_name = extracted_entities[0] if extracted_entities else None
            
            # Generate summary for tooltip
            summary = _generate_summary(src["text"])
            
            citation = Citation(
                uuid=citation_uuid,
                text=src["text"],
                source_doc=src["source_doc"],
                page_number=src["page_number"],
                law_type=src["law_type"],
                score=src["score"],
                entity_name=primary_entity_name,
                summary=summary
            )
            
            citations.append(citation)
            
            # Map all found entities to this citation UUID for graph linking
            for ent in extracted_entities:
                citation_map[ent] = citation_uuid
        
        # Build graph data if requested
        graph_data = None
        if request.include_graph_data:
            graph_data = _build_enhanced_graph_data(
                orchestrator,
                result,
                citation_map
            )
        
        response = QueryResponse(
            answer=result["answer"],
            citations=citations,
            metadata=result["metadata"],
            graph_data=graph_data
        )
        
        logger.info(f"Query processed successfully. Citations: {len(citations)}")
        return response
        
    except Exception as e:
        logger.error(f"Error processing query: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error processing query: {str(e)}"
        )


def _generate_summary(text: str, max_length: int = 150) -> str:
    """
    Generate a short summary for UI tooltips.
    
    Args:
        text: Full text to summarize
        max_length: Maximum length of summary
        
    Returns:
        Summary text
    """
    # Simple truncation with ellipsis
    # In production, you could use an LLM for better summaries
    if len(text) <= max_length:
        return text
    
    # Find last complete sentence within limit
    truncated = text[:max_length]
    last_period = truncated.rfind('.')
    
    if last_period > max_length * 0.5:  # If we have at least half the text
        return text[:last_period + 1]
    else:
        return truncated.rstrip() + "..."


def _extract_entities_from_text(text: str, orchestrator: Optional[LegalRAGOrchestrator] = None) -> List[str]:
    """
    Extract legal entities from text using Regex and Graph Node matching.
    
    Args:
        text: Text to extract entities from
        orchestrator: Optional orchestrator to access the knowledge graph
        
    Returns:
        List of extracted entity names
    """
    import re
    entities = set()
    
    # 1. Regex based extraction (High confidence)
    patterns = [
        r'Section\s+\d+[A-Z]?',
        r'Article\s+\d+[A-Z]?',
        r'Part\s+[IVX]+',
        r'Chapter\s+[IVX]+',
        r'Order\s+[IVX]+',
        r'Rule\s+\d+',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            # Normalize basic spacing
            clean_match = " ".join(match.split())
            entities.add(clean_match)

    # 2. Graph Node matching (Contextual)
    if orchestrator and orchestrator.graph_expander and orchestrator.graph_expander.graph:
        graph = orchestrator.graph_expander.graph
        
        # We process text once to lower case for faster matching
        text_lower = text.lower()
        
        for node in graph.nodes():
            # Skip short/noisy nodes
            if len(node) < 4 or node.isdigit():
                continue
                
            # Skip nodes that are likely just numbers or single words that are common
            if node.lower() in ["the", "and", "act", "law", "part", "section", "article"]:
                continue

            # Check if node exists in text
            # Use specific boundary checks for better accuracy
            # Regex escape the node name to handle special chars
            try:
                if re.search(r'\b' + re.escape(node) + r'\b', text, re.IGNORECASE):
                    entities.add(node)
                elif node.lower() in text_lower: # Fallback for non-word boundary cases
                     entities.add(node)
            except Exception:
                continue
                
    return list(entities)


def _build_enhanced_graph_data(
    orchestrator: LegalRAGOrchestrator,
    result: Dict,
    citation_map: Dict[str, str]
) -> GraphData:
    """
    Build enhanced graph visualization data with linked citations.
    
    Args:
        orchestrator: The orchestrator instance
        result: Query result from orchestrator
        citation_map: Mapping of entity names to citation UUIDs
        
    Returns:
        GraphData with nodes, edges, and metadata
    """
    nodes = []
    edges = []
    
    # Get retrieved documents to extract entities
    retrieved_docs = result.get("sources", [])
    
    # Extract entities from retrieved docs
    entities_in_context = set()
    for doc in retrieved_docs:
        extracted = _extract_entities_from_text(doc["text"], orchestrator)
        entities_in_context.update(extracted)
    
    # Also add expanded entities from the orchestrator result metadata
    expanded_entities = result.get("metadata", {}).get("expanded_entities", [])
    # Convert expanded_entities to list of strings if they are objects
    # Based on orchestrator logic, they are strings
    entities_in_context.update(expanded_entities)

    processed_node_ids = set()

    # Build nodes for entities in context
    for entity in entities_in_context:
        if entity in processed_node_ids:
            continue
            
        # Check if this entity has a citation UUID
        # citation_map keys might be case sensitive, let's try fuzzy match if needed
        citation_uuid = citation_map.get(entity)
        
        # Get relationships for this entity from the graph
        relationships = orchestrator.graph_expander.get_entity_relationships(entity)
        
        # Build tooltip metadata
        tooltip_lines = [f"**{entity}**"]
        if relationships:
            tooltip_lines.append(f"Connections: {len(relationships)}")
            # Add first few relationships
            for rel in relationships[:3]:
                # Determine direction for display
                arrow = "→" if rel['direction'] == 'outgoing' else "←"
                other = rel['object'] if rel['direction'] == 'outgoing' else rel['subject']
                tooltip_lines.append(f"{arrow} {rel['predicate']}: {other}")
        else:
             tooltip_lines.append("No direct connections found in graph.")
        
        node = GraphNode(
            id=entity,
            label=entity,
            type="cited_entity" if citation_uuid else "entity",
            citation_uuid=citation_uuid,
            metadata={
                "tooltip": "\n".join(tooltip_lines),
                "relationship_count": len(relationships),
                "is_cited": citation_uuid is not None
            }
        )
        nodes.append(node)
        processed_node_ids.add(entity)
        
        # Add edges for this entity
        # We limit to 5 relationships per entity to prevent graph explosion in UI
        for rel in relationships[:5]:  
            if rel['direction'] == 'outgoing':
                edge = GraphEdge(
                    source=entity,
                    target=rel['object'],
                    relation=rel['predicate'],
                    label=rel['predicate']
                )
                target_entity = rel['object']
            else:
                edge = GraphEdge(
                    source=rel['subject'],
                    target=entity,
                    relation=rel['predicate'],
                    label=rel['predicate']
                )
                target_entity = rel['subject']
            
            edges.append(edge)
            
            # Add target node if not already in nodes
            if target_entity not in processed_node_ids:
                # Add basic target node
                target_node = GraphNode(
                    id=target_entity,
                    label=target_entity,
                    type="related_entity",
                    metadata={
                        "tooltip": f"**{target_entity}**\nRelated to {entity}",
                        "is_cited": False
                    }
                )
                nodes.append(target_node)
                processed_node_ids.add(target_entity)
    
    # Build stats
    stats = {
        "total_nodes": len(nodes),
        "total_edges": len(edges),
        "cited_nodes": len([n for n in nodes if n.citation_uuid]),
        "relationship_types": list(set(e.relation for e in edges))
    }
    
    return GraphData(
        nodes=nodes,
        edges=edges,
        stats=stats
    )


@app.post("/audit")
async def audit_document_endpoint(file: UploadFile = File(...)):
    """
    Audit uploaded legal document for compliance.
    CHECKS:
    1. Extracts text from PDF/TXT.
    2. Identifies cited laws.
    3. Cross-references with Knowledge Graph for outdated (Legacy) provisions.
    """
    if not audit_agent:
        raise HTTPException(status_code=503, detail="Audit service unavailable")
    
    filename = file.filename or "uploaded_doc"
    temp_dir = "data/temp"
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = os.path.join(temp_dir, filename)
    
    try:
        content = await file.read()
        with open(temp_path, "wb") as f:
            f.write(content)
            
        # Extract text
        text_content = ""
        try:
            # Try unstructured first (it's in requirements.txt)
            if filename.lower().endswith(".pdf"):
                from unstructured.partition.auto import partition
                elements = partition(filename=temp_path)
                text_content = "\n\n".join([str(e) for e in elements]) 
            else:
                # Assume text for others
                text_content = content.decode("utf-8", errors="ignore")
        except Exception as e:
            logger.warning(f"Complex extraction failed: {e}. Fallback to text decode.")
            text_content = content.decode("utf-8", errors="ignore")
        
        if len(text_content) < 10:
             raise HTTPException(400, "Could not extract sufficient text from document.")

        result = audit_agent.audit_document(text_content, filename)
        return result
        
    except Exception as e:
        logger.error(f"Audit failed: {e}")
        raise HTTPException(500, f"Audit failed: {str(e)}")
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass


# Development server
if __name__ == "__main__":
    logger.info("Starting Dharma-Setu Legal RAG API...")
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
