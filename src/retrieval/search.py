import os
import logging
from typing import List, Dict
from dotenv import load_dotenv

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from qdrant_client import QdrantClient

import sys
sys.path.append(os.getcwd())
from src.retrieval.vectordb import get_qdrant_client, COLLECTION_NAME

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

QDRANT_PATH = "data/qdrant_db"
EMBEDDING_MODEL = "models/text-embedding-004"

def get_embeddings_model():
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not found")
    return GoogleGenerativeAIEmbeddings(model=EMBEDDING_MODEL, google_api_key=api_key)

def search_legal_docs(query: str, limit: int = 5):
    """Search for relevant legal documents."""
    client = QdrantClient(path=QDRANT_PATH)
    embeddings = get_embeddings_model()
    
    logger.info(f"🔍 Query: {query}")
    query_vector = embeddings.embed_query(query)
    
    try:
        # Use query_points which is the compatible method for this Qdrant version/setup
        results = client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            limit=limit
        ).points
    except Exception as e:
        logger.error(f"Search failed: {e}")
        available = [m for m in dir(client) if 'search' in m or 'query' in m]
        logger.info(f"Available methods: {available}")
        raise

    logger.info(f"✅ Found {len(results)} results:\n")
    
    for i, hit in enumerate(results, 1):
        payload = hit.payload
        text = payload.get("text", "No text content")
        # Handle sources - filename might be in metadata
        source = payload.get("source_doc", "Unknown source")
        page = payload.get("page_number", "?")
        type_ = payload.get("law_type", "Unknown")
        score = hit.score
        
        print(f"[{i}] Score: {score:.4f} | Source: {source} (Page {page}) | Type: {type_}")
        print(f"    {text[:200].replace(chr(10), ' ')}...")
        print("-" * 50)

if __name__ == "__main__":
    # Test query
    search_legal_docs("What are the fundamental rights of a citizen?")
