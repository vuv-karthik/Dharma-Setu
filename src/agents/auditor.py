"""
Document Audit Agent for Legal Compliance
"""
import os
import re
import pickle
import logging
from typing import TypedDict, List, Dict, Any
from dotenv import load_dotenv

from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
import networkx as nx

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

GRAPH_PICKLE_PATH = "data/processed/legal_graph.gpickle"
MODEL_NAME = "gemini-2.0-flash-exp"

class AuditState(TypedDict):
    text_content: str
    filename: str
    citations: List[str]
    findings: List[Dict]
    final_report: Dict

class AuditAgent:
    def __init__(self):
        self.graph = self._load_graph()
        self.llm = self._init_llm()
        self.workflow = self._build_workflow()

    def _load_graph(self) -> nx.DiGraph:
        if not os.path.exists(GRAPH_PICKLE_PATH):
            logger.warning(f"Graph not found at {GRAPH_PICKLE_PATH}. Audit features limited.")
            return nx.DiGraph()
        with open(GRAPH_PICKLE_PATH, 'rb') as f:
            return pickle.load(f)

    def _init_llm(self):
        api_key = os.getenv("GOOGLE_API_KEY")
        return ChatGoogleGenerativeAI(model=MODEL_NAME, google_api_key=api_key, temperature=0.0)

    def extract_citations(self, state: AuditState) -> AuditState:
        """Node 1: Extract legal citations from text."""
        text = state["text_content"]
        
        # Regex Heuristic for speed
        pattern = r'(?:Section|Article|Order|Rule)\s+\d+(?:[A-Z])?(?:\s+(?:of|under|read with))?\s*(?:IPC|BNS|Constitution|Code|Act)?'
        matches = re.findall(pattern, text, re.IGNORECASE)
        
        # Deduplicate and clean
        citations = list(set([m.strip() for m in matches if len(m) < 50]))
        
        state["citations"] = citations
        logger.info(f"Extracted {len(citations)} citations.")
        return state

    def verify_compliance(self, state: AuditState) -> AuditState:
        """Node 2: Check against Knowledge Graph Bridge."""
        citations = state["citations"]
        graph = self.graph
        findings = []
        
        for citation in citations:
            matched_node = None
            citation_upper = citation.upper()
            
            # Simple fuzzy match against graph nodes
            for node in graph.nodes():
                # Check if citation contains node or vice versa?
                # "Section 302 IPC" vs "Section 302"
                n_str = str(node).upper()
                if n_str in citation_upper and len(n_str) > 5:
                    matched_node = node
                    break
            
            if matched_node:
                # Check for EQUIVALENT_TO edges
                if graph.has_node(matched_node):
                    out_edges = graph.out_edges(matched_node, data=True)
                    for u, v, data in out_edges:
                        if data.get('relation') == 'EQUIVALENT_TO':
                            target_regime = graph.nodes[v].get('regime', 'Unknown')
                            source_regime = graph.nodes[u].get('regime', 'Unknown')
                            
                            if source_regime == 'Legacy' and target_regime == 'Current':
                                findings.append({
                                    "citation": citation,
                                    "status": "OUTDATED",
                                    "suggestion": v, 
                                    "reasoning": f"Provision {u} replaced by {v}.",
                                    "severity": "HIGH"
                                })
                                break
            else:
                if "IPC" in citation_upper and "1860" not in citation_upper:
                     findings.append({
                        "citation": citation,
                        "status": "WARNING",
                        "suggestion": "Check BNS Equivalent",
                        "reasoning": "Legacy IPC reference detected.",
                        "severity": "MEDIUM"
                    })

        state["findings"] = findings
        return state

    def _build_workflow(self) -> StateGraph:
        workflow = StateGraph(AuditState)
        workflow.add_node("extract_citations", self.extract_citations)
        workflow.add_node("verify_compliance", self.verify_compliance)
        
        workflow.set_entry_point("extract_citations")
        workflow.add_edge("extract_citations", "verify_compliance")
        workflow.add_edge("verify_compliance", END)
        
        return workflow.compile()

    def audit_document(self, text_content: str, filename: str) -> Dict:
        initial_state = {
            "text_content": text_content,
            "filename": filename,
            "citations": [],
            "findings": [],
            "final_report": {}
        }
        final_state = self.workflow.invoke(initial_state)
        return {
            "filename": filename,
            "findings": final_state["findings"],
            "total_citations": len(final_state["citations"])
        }
