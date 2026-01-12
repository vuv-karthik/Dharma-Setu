"""
LangGraph Orchestrator for Legal RAG with Graph Expansion

This module orchestrates the complete RAG pipeline:
1. Vector retrieval from Qdrant
2. Graph-based context expansion
3. Answer generation with Gemini
"""

import os
import sys
import logging
from typing import TypedDict, List, Dict, Annotated
from dotenv import load_dotenv

from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.messages import HumanMessage, SystemMessage

# Add src to path for imports
sys.path.append(os.getcwd())
from src.retrieval.vectordb import get_qdrant_client, COLLECTION_NAME
from src.agents.graph_expander import GraphContextExpander

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

# Configuration
EMBEDDING_MODEL = "models/text-embedding-004"
EMBEDDING_MODEL = "models/text-embedding-004"
ANSWER_MODEL = "gemini-2.5-flash"
DRAFTER_MODEL = "gemini-1.5-pro"


class AgentState(TypedDict):
    """State tracked throughout the agent workflow."""
    query: str
    retrieved_docs: List[Dict]
    expanded_entities: List[str]
    graph_context: List[Dict]
    final_answer: str
    metadata: Dict
    language: str
    input_language: str
    translated_query: str


class LegalRAGOrchestrator:
    """Orchestrates the legal RAG pipeline using LangGraph."""
    
    def __init__(self):
        """Initialize the orchestrator with all required components."""
        self.qdrant_client = get_qdrant_client()
        self.embeddings = self._init_embeddings()
        self.graph_expander = GraphContextExpander()
        self.answer_llm = self._init_answer_llm()
        self.graph_expander = GraphContextExpander()
        self.answer_llm = self._init_answer_llm()
        self.drafter_llm = self._init_drafter_llm()
        self.workflow = self._build_workflow()
        self.drafting_workflow = self._build_drafting_workflow()
        
    def _init_embeddings(self):
        """Initialize embedding model."""
        api_key = os.getenv("GOOGLE_API_KEY")
        return GoogleGenerativeAIEmbeddings(
            model=EMBEDDING_MODEL,
            google_api_key=api_key
        )
    
    def _init_answer_llm(self):
        """Initialize Gemini 2.5 Flash for answer generation."""
        api_key = os.getenv("GOOGLE_API_KEY")
        return ChatGoogleGenerativeAI(
            model=ANSWER_MODEL,
            google_api_key=api_key,
            temperature=0.3,
            convert_system_message_to_human=True
        )

    def _init_drafter_llm(self):
        """Initialize Gemini 1.5 Pro for complex drafting."""
        api_key = os.getenv("GOOGLE_API_KEY")
        # Note: 1.5 Pro is better for long context and reasoning
        return ChatGoogleGenerativeAI(
            model=DRAFTER_MODEL,
            google_api_key=api_key,
            temperature=0.2, # Lower temp for formal drafting
            convert_system_message_to_human=True
        )
    
    def _translate_query(self, query: str) -> str:
        """Translate non-English query to English for retrieval."""
        try:
            prompt = f"Translate the following legal query to English. Return ONLY the English translation, no other text. Query: {{query}}"
            response = self.answer_llm.invoke(prompt)
            return response.content.strip()
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            return query

    def retrieve_vectors(self, state: AgentState) -> AgentState:
        """
        Node 1: Retrieve relevant documents from Qdrant.
        """
        query = state["query"]
        
        # Translate if needed
        if state.get("input_language") and state["input_language"] != "English":
            logger.info(f"Translating input from {state['input_language']}...")
            translated = self._translate_query(query)
            state["translated_query"] = translated
            logger.info(f"Translated: {query} -> {translated}")
            query = translated # Use English for retrieval

        logger.info(f"\n{'='*70}")
        logger.info(f"NODE 1: Vector Retrieval")
        logger.info(f"Query: {query}")
        logger.info(f"{'='*70}")
        
        # Generate query embedding
        query_vector = self.embeddings.embed_query(query)
        
        # Search Qdrant
        results = self.qdrant_client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            limit=5
        ).points
        
        # Extract documents
        retrieved_docs = []
        for hit in results:
            retrieved_docs.append({
                "text": hit.payload.get("text", ""),
                "source_doc": hit.payload.get("source_doc", "Unknown"),
                "page_number": hit.payload.get("page_number", "?"),
                "law_type": hit.payload.get("law_type", "Unknown"),
                "score": hit.score
            })
        
        logger.info(f"Retrieved {len(retrieved_docs)} documents")
        for i, doc in enumerate(retrieved_docs, 1):
            logger.info(f"  {i}. {doc['source_doc']} (Page {doc['page_number']}) - Score: {doc['score']:.4f}")
        
        state["retrieved_docs"] = retrieved_docs
        state["metadata"] = {"retrieval_count": len(retrieved_docs)}
        
        return state
    
    def expand_with_graph(self, state: AgentState) -> AgentState:
        """
        Node 2: Expand context using knowledge graph.
        """
        logger.info(f"\n{'='*70}")
        logger.info(f"NODE 2: Graph-based Context Expansion")
        logger.info(f"{'='*70}")
        
        query = state["query"]
        retrieved_docs = state["retrieved_docs"]
        
        # Decision: Should we expand?
        should_expand, reasoning = self.graph_expander.should_expand_context(
            query, retrieved_docs
        )
        
        logger.info(f"Expansion Decision: {'YES' if should_expand else 'NO'}")
        logger.info(f"Reasoning: {reasoning}")
        
        expanded_entities = []
        graph_context = []
        
        if should_expand:
            # Get related entities from graph
            expanded_entities = self.graph_expander.expand_context(retrieved_docs)
            logger.info(f"Found {len(expanded_entities)} related entities")
            
            # Get relationships for expanded entities
            for entity in expanded_entities[:10]:  # Limit to top 10
                relationships = self.graph_expander.get_entity_relationships(entity)
                if relationships:
                    graph_context.append({
                        "entity": entity,
                        "relationships": relationships[:5]  # Top 5 relationships
                    })
                    logger.info(f"  {entity}: {len(relationships)} relationships")
        
        state["expanded_entities"] = expanded_entities
        state["graph_context"] = graph_context
        state["metadata"]["expansion_performed"] = should_expand
        state["metadata"]["expanded_entity_count"] = len(expanded_entities)
        
        return state
    
    def generate_answer(self, state: AgentState) -> AgentState:
        """
        Node 3: Generate final answer using all context.
        """
        logger.info(f"\n{'='*70}")
        logger.info(f"NODE 3: Answer Generation")
        logger.info(f"{'='*70}")
        
        query = state["query"]
        retrieved_docs = state["retrieved_docs"]
        graph_context = state["graph_context"]
        
        # Format context for the LLM
        vector_context = "\n\n".join([
            f"**Source: {doc['source_doc']} (Page {doc['page_number']})**\n{doc['text']}"
            for doc in retrieved_docs
        ])
        
        graph_context_str = ""
        if graph_context:
            graph_context_str = "\n\n**Related Legal Provisions (from Knowledge Graph):**\n"
            for item in graph_context:
                entity = item["entity"]
                rels = item["relationships"]
                graph_context_str += f"\n{entity}:\n"
                for rel in rels:
                    graph_context_str += f"  - {rel['subject']} --[{rel['predicate']}]--> {rel['object']}\n"
        
        system_prompt = """You are an expert legal assistant specializing in Indian law. Your goal is to provide **concise, visual, and structured** answers.

**CORE PRINCIPLES:**
1. **NO WALLS OF TEXT**: Avoid long paragraphs. Use bullet points for almost everything.
2. **FLOWCHARTS FIRST**: If the query involves a process (e.g., arrest, appeal, investigation), START with a Mermaid flowchart.
3. **STEP-BY-STEP**: Break down procedures into numbered steps.

**Instructions:**
1. **Analyze** the context.
2. **Format** your response:
   - **Executive Summary**: 1-2 sentences max.
   - **Visual Flow**: (Mermaid Diagram - **CRITICAL: Quote all node labels**)
   - **Key Steps/Provisions**: Bulleted list with **Bold** terms.
   - **Citations**: Mention Sections/Articles clearly.

**Mermaid Requirement:**
- Enclose all node labels in double quotes.
- Example:
  ```mermaid
  graph TD
    A["Start"] --> B["Action"]
  ```

**Be precise, minimize text, maximize clarity.**"""

        # Dynamic Instruction for Bridge Links
        if "EQUIVALENT_TO" in graph_context_str:
            system_prompt += """

**LEGAL BRIDGE DETECTED:**
- The context includes a mapping between IPC (Old) and BNS (New) laws (EQUIVALENT_TO).
- **MANDATORY**: Create a Markdown comparison table titled "**Legacy (IPC) vs Current (BNS)**".
- Columns: | Feature | IPC Section | BNS Section | Key Changes |
- Highlight distinct changes in definition, penalty, or scope.
"""

        # Dynamic Instruction for Language
        language = state.get("language", "English")
        if language and language != "English":
            system_prompt += f"""

**LANGUAGE INSTRUCTION:**
- Provide the final answer in **{language}**.
- Ensure legal terms are explained clearly in {language} (use English terms in brackets if necessary for clarity).
- Maintain the Markdown structure and Mermaid diagrams.
"""

        user_prompt = f"""**Question:** {query}

**Retrieved Legal Context:**
{vector_context}

{graph_context_str}

**Please provide a visual, step-by-step legal answer:**"""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        logger.info("Generating answer with Gemini 2.5 Flash...")
        response = self.answer_llm.invoke(messages)
        final_answer = response.content
        
        state["final_answer"] = final_answer
        logger.info("Answer generated successfully")
        
        return state
    
    def generate_legal_memo(self, state: AgentState) -> AgentState:
        """
        Node 3 (Draft): Generate a formal Written Submission.
        """
        query = state["query"]
        vector_context = "\n\n".join([f"Source: {d['source_doc']}\nText: {d['text']}" for d in state["retrieved_docs"]])
        
        # Build graph context string
        graph_context = state["graph_context"]
        graph_context_str = ""
        if graph_context:
            graph_context_str = "Also consider these Legal Cross-References:\n"
            for item in graph_context:
                graph_context_str += f"- {item['entity']} relates to {', '.join([r['object'] for r in item['relationships']])}\n"
        
        system_prompt = """You are a Senior Advocate of the Supreme Court of India. 
Your task is to draft a formal **Written Submission** (Legal Memo) based on the provided facts.

**STRUCTURE:**
1. **Title**: IN THE HON'BLE COURT OF [Appropriate Forum]
2. **Subject**: Written Submission on behalf of the [Petitioner/Respondent]
3. **Brief Facts**: concise summary of the case facts.
4. **Issues for Consideration**: Numbered list of legal questions.
5. **Submissions**: 
   - Detailed legal arguments.
   - **MANDATORY**: Cite sections clearly (e.g., "Section 302 of IPC").
   - Use the provided Graph Cross-References to strengthen arguments.
6. **Prayers**: The specific relief sought.

**TONE**: Formal, authoritative, precise, and persuasive. 
**LANGUAGE**: {language} (if specified, otherwise English).

**CRITICAL**: 
- Do not invent facts.
- Rely on the Retreived Context.
"""
        language = state.get("language", "English")
        if language and language != "English":
             system_prompt += f"\n**TRANSLATION**: Draft the entire submission in {language}, using appropriate legal terminology."

        user_prompt = f"""**Facts of the Case:** {query}

**Relevant Legal Precedents & Sections:**
{vector_context}

{graph_context_str}

**Draft the Written Submission:**"""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        logger.info("Drafting Legal Memo with Gemini 1.5 Pro...")
        response = self.drafter_llm.invoke(messages)
        state["final_answer"] = response.content
        return state

    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow."""
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("retrieve_vectors", self.retrieve_vectors)
        workflow.add_node("expand_with_graph", self.expand_with_graph)
        workflow.add_node("generate_answer", self.generate_answer)
        
        # Define edges (flow)
        workflow.set_entry_point("retrieve_vectors")
        workflow.add_edge("retrieve_vectors", "expand_with_graph")
        workflow.add_edge("expand_with_graph", "generate_answer")
        workflow.add_edge("generate_answer", END)
        
        return workflow.compile()

    def _build_drafting_workflow(self) -> StateGraph:
        """Build the dedicated Legal Drafter workflow."""
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("retrieve_vectors", self.retrieve_vectors)
        workflow.add_node("expand_with_graph", self.expand_with_graph)
        workflow.add_node("generate_legal_memo", self.generate_legal_memo) # New Node
        
        # Define edges (flow)
        workflow.set_entry_point("retrieve_vectors")
        workflow.add_edge("retrieve_vectors", "expand_with_graph")
        workflow.add_edge("expand_with_graph", "generate_legal_memo")
        workflow.add_edge("generate_legal_memo", END)
        
        return workflow.compile()
    
    def query(self, user_query: str, language: str = "English", input_language: str = "English") -> Dict:
        """
        Execute the complete RAG pipeline for a user query.
        
        Args:
            user_query: The user's legal question
            language: Target language for the answer
            input_language: Language of the input query
            
        Returns:
            Dictionary with final_answer and metadata
        """
        logger.info(f"\n{'#'*70}")
        logger.info(f"# LEGAL RAG ORCHESTRATOR")
        logger.info(f"{'#'*70}")
        
        # Initialize state
        initial_state = {
            "query": user_query,
            "retrieved_docs": [],
            "expanded_entities": [],
            "graph_context": [],
            "final_answer": "",
            "metadata": {},
            "language": language,
            "input_language": input_language,
            "translated_query": ""
        }
        
        # Run workflow
        final_state = self.workflow.invoke(initial_state)
        
        logger.info(f"\n{'='*70}")
        logger.info(f"WORKFLOW COMPLETE")
        logger.info(f"{'='*70}")
        logger.info(f"Metadata: {final_state['metadata']}")
        
        return {
            "answer": final_state["final_answer"],
            "metadata": final_state["metadata"],
            "sources": final_state["retrieved_docs"]
        }

    def draft(self, facts: str, language: str = "English", input_language: str = "English") -> Dict:
        """
        Execute the Legal Drafter workflow.
        """
        logger.info(f"\n{'#'*70}")
        logger.info(f"# LEGAL DRAFTER AGENT (Facts -> Memo)")
        logger.info(f"{'#'*70}")
        
        initial_state = {
            "query": facts, # In drafting mode, query = facts
            "retrieved_docs": [],
            "expanded_entities": [],
            "graph_context": [],
            "final_answer": "",
            "metadata": {},
            "language": language,
            "input_language": input_language,
            "translated_query": ""
        }
        
        final_state = self.drafting_workflow.invoke(initial_state)
        
        return {
            "answer": final_state["final_answer"], # This is the Memo
            "metadata": final_state["metadata"],
            "sources": final_state["retrieved_docs"]
        }


def main():
    """Test the orchestrator with a complex query."""
    orchestrator = LegalRAGOrchestrator()
    
    # Test query
    query = "What are the legal implications of disturbing a religious assembly?"
    
    logger.info(f"\n{'*'*70}")
    logger.info(f"TEST QUERY: {query}")
    logger.info(f"{'*'*70}\n")
    
    # Execute
    result = orchestrator.query(query)
    
    # Display results
    print(f"\n{'='*70}")
    print(f"FINAL ANSWER:")
    print(f"{'='*70}")
    print(result["answer"])
    print(f"\n{'='*70}")
    print(f"SOURCES:")
    print(f"{'='*70}")
    for i, source in enumerate(result["sources"], 1):
        print(f"{i}. {source['source_doc']} (Page {source['page_number']}) - Score: {source['score']:.4f}")
    print(f"\n{'='*70}")
    print(f"METADATA:")
    print(f"{'='*70}")
    for key, value in result["metadata"].items():
        print(f"  {key}: {value}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
