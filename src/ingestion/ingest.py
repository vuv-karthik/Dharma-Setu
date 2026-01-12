import os
import json
import time
import logging
from typing import List, Dict
from dotenv import load_dotenv

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from qdrant_client.models import PointStruct

# Import shared Qdrant config
# Note: In a real package structure, this might need sys.path adjustment or relative import
# allowing simple absolute import here assuming src is in path or run from root
import sys
sys.path.append(os.getcwd())
from src.retrieval.vectordb import get_qdrant_client, COLLECTION_NAME

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configuration
EMBEDDING_MODEL = "models/text-embedding-004"  # Updated to newer model per user request
PARSED_DATA_PATH = "data/processed/parsed_elements.json"

def get_embeddings_model():
    """Initialize Google GenAI Embeddings."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not found in environment variables")
    return GoogleGenerativeAIEmbeddings(model=EMBEDDING_MODEL, google_api_key=api_key)

def enrich_metadata(element: Dict) -> Dict:
    """
    Add 'Smart Metadata' fields: source_doc, element_type, page_number, law_type.
    """
    raw_meta = element.get("metadata", {})
    filename = raw_meta.get("filename", "unknown.pdf")
    
    # Smart Metadata Strategy
    enriched = {
        "text": element.get("text", ""),
        "element_id": element.get("element_id"),
        "page_number": raw_meta.get("page_number", 0),
        "source_doc": filename.replace(".pdf", ""),  # e.g., "Bharatiya_Nyaya_Sanhita_2023"
        "element_type": element.get("type", "Text"), # e.g., "Title", "NarrativeText" -> mapped to generic if needed
        "last_modified": raw_meta.get("last_modified"),
        # Custom logic for law_type
        "law_type": "Constitutional" if "Constitution" in filename else "Statute"
    }
    
    return enriched

def process_and_ingest():
    """Read parsed data, enrich metadata, embed, and upload."""
    if not os.path.exists(PARSED_DATA_PATH):
        logger.error(f"Parsed data not found at {PARSED_DATA_PATH}")
        return

    logger.info(f"Loading data from {PARSED_DATA_PATH}...")
    with open(PARSED_DATA_PATH, 'r', encoding='utf-8') as f:
        elements = json.load(f)

    logger.info(f"Loaded {len(elements)} raw elements. Enriching metadata...")
    
    embeddings = get_embeddings_model()
    client = get_qdrant_client()
    
    batch_size = 20
    points: List[PointStruct] = []
    
    for i in range(0, len(elements), batch_size):
        if i > 0:
            time.sleep(1.0) # Rate limit safety
            
        batch = elements[i : i + batch_size]
        
        # Prepare batch mapping: enriched metadata and texts
        valid_items = []
        texts_to_embed = []
        
        for el in batch:
            text = el.get("text", "").strip()
            if len(text) < 10: # Skip noise
                continue
                
            meta = enrich_metadata(el)
            valid_items.append(meta)
            texts_to_embed.append(text)
            
        if not texts_to_embed:
            continue
            
        try:
            # Generate vectors
            vectors = embeddings.embed_documents(texts_to_embed)
            
            # Create Qdrant points
            for idx, (meta, vector) in enumerate(zip(valid_items, vectors)):
                # unique integer ID logic: i (batch_start) + idx
                point_id = i + idx 
                
                points.append(PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=meta
                ))
                
        except Exception as e:
            logger.error(f"Error embedding batch {i}: {e}")
            continue

        # Upsert whenever we have a decent chunk or at the end
        if len(points) >= 100 or (i + batch_size >= len(elements)):
            try:
                client.upsert(
                    collection_name=COLLECTION_NAME,
                    points=points
                )
                logger.info(f"Refreshed {len(points)} points to '{COLLECTION_NAME}'.")
                points = []
            except Exception as e:
                logger.error(f"Failed to upsert to Qdrant: {e}")

    logger.info("Ingestion complete!")

if __name__ == "__main__":
    process_and_ingest()
