from qdrant_client import QdrantClient
from qdrant_client.http import models
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
QDRANT_PATH = "data/qdrant_db"  # Local persistence
COLLECTION_NAME = "nyaya_flow_core"
VECTOR_SIZE = 768

def get_qdrant_client() -> QdrantClient:
    """Get or create Qdrant client."""
    return QdrantClient(path=QDRANT_PATH)

def setup_collection():
    """Initialize the collection with specific configuration."""
    client = get_qdrant_client()
    
    # Check if collection exists to avoid unnecessary recreation (optional, but good for idempotency)
    # The user instruction uses recreate_collection which wipes data. 
    # useful for fresh setup, but careful for production.
    # We will follow the instruction directly to be compliant.
    
    logger.info(f"Initializing collection '{COLLECTION_NAME}'...")
    
    client.recreate_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=models.VectorParams(
            size=VECTOR_SIZE, 
            distance=models.Distance.COSINE
        ),
    )
    logger.info(f"✅ Collection '{COLLECTION_NAME}' is ready.")

if __name__ == "__main__":
    setup_collection()
