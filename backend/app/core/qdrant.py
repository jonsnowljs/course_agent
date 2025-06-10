from qdrant_client import QdrantClient
from app.core.config import settings

qdrant_client: QdrantClient | None = None


def get_qdrant_client() -> QdrantClient:
    """
    Get or create a Qdrant client instance.
    Returns a singleton instance of QdrantClient.
    """
    global qdrant_client
    if qdrant_client is None:
        qdrant_client = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY,
        )
    return qdrant_client 
