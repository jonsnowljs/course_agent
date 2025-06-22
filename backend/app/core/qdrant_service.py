from typing import List, Dict, Any, Optional
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from app.core.qdrant import get_qdrant_client
from app.core.embeddings import create_document_chunks, generate_embeddings
from app.core.config import settings

DOCUMENTS_COLLECTION = "documents"

def get_embedding_dimension() -> int:
    """Get the embedding dimension based on the OpenAI model."""
    model_dimensions = {
        "text-embedding-3-small": 1536,
        "text-embedding-3-large": 3072,
        "text-embedding-ada-002": 1536,
    }
    return model_dimensions.get(settings.OPENAI_EMBEDDING_MODEL, 1536)

def ensure_collection_exists():
    """Ensure the documents collection exists in Qdrant."""
    client = get_qdrant_client()
    
    try:
        client.get_collection(DOCUMENTS_COLLECTION)
    except Exception:
        # Collection doesn't exist, create it
        embedding_dim = get_embedding_dimension()
        client.create_collection(
            collection_name=DOCUMENTS_COLLECTION,
            vectors_config=VectorParams(
                size=embedding_dim,  # Dimension for OpenAI embedding models
                distance=Distance.COSINE
            )
        )

def store_document(content: str, filename: str, user_id: str) -> Dict[str, Any]:
    """Store a document in Qdrant by chunking and embedding it."""
    ensure_collection_exists()
    
    # Create document chunks with embeddings
    chunks = create_document_chunks(content, filename, user_id)
    
    if not chunks:
        raise ValueError("No chunks were created from the document")
    
    client = get_qdrant_client()
    
    # Convert chunks to PointStruct objects
    points = []
    for chunk in chunks:
        point = PointStruct(
            id=chunk["id"],
            vector=chunk["vector"],
            payload=chunk["payload"]
        )
        points.append(point)
    
    # Store points in Qdrant
    client.upsert(
        collection_name=DOCUMENTS_COLLECTION,
        points=points
    )
    
    return {
        "document_id": chunks[0]["payload"]["document_id"],
        "filename": filename,
        "chunks_count": len(chunks),
        "total_words": sum(chunk["payload"]["chunk_word_count"] for chunk in chunks)
    }

def search_documents(query: str, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Search for similar documents using vector similarity."""
    ensure_collection_exists()
    
    # Generate embedding for the query
    query_embeddings = generate_embeddings([query])
    query_vector = query_embeddings[0]
    
    client = get_qdrant_client()
    
    # Search with user filter
    search_results = client.search(
        collection_name=DOCUMENTS_COLLECTION,
        query_vector=query_vector,
        query_filter=Filter(
            must=[
                FieldCondition(
                    key="user_id",
                    match=MatchValue(value=user_id)
                )
            ]
        ),
        limit=limit,
        with_payload=True
    )
    
    return [
        {
            "id": result.id,
            "score": result.score,
            "filename": result.payload.get("filename"),
            "chunk_text": result.payload.get("chunk_text"),
            "document_id": result.payload.get("document_id"),
            "chunk_index": result.payload.get("chunk_index"),
            "created_at": result.payload.get("created_at")
        }
        for result in search_results
    ]

def get_user_documents(user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Get all documents for a user (grouped by document_id)."""
    ensure_collection_exists()
    
    client = get_qdrant_client()
    
    # Scroll through all points for the user
    scroll_result = client.scroll(
        collection_name=DOCUMENTS_COLLECTION,
        scroll_filter=Filter(
            must=[
                FieldCondition(
                    key="user_id",
                    match=MatchValue(value=user_id)
                )
            ]
        ),
        limit=limit,
        with_payload=True
    )
    
    # Group by document_id to get unique documents
    documents = {}
    for point in scroll_result[0]:  # scroll_result is a tuple (points, next_page_offset)
        doc_id = point.payload.get("document_id")
        if doc_id not in documents:
            documents[doc_id] = {
                "document_id": doc_id,
                "filename": point.payload.get("filename"),
                "created_at": point.payload.get("created_at"),
                "chunks_count": 1,
                "total_words": point.payload.get("chunk_word_count", 0)
            }
        else:
            documents[doc_id]["chunks_count"] += 1
            documents[doc_id]["total_words"] += point.payload.get("chunk_word_count", 0)
    
    return list(documents.values())

def delete_document(document_id: str, user_id: str) -> bool:
    """Delete all chunks of a specific document."""
    ensure_collection_exists()
    
    client = get_qdrant_client()
    
    # First, find all points for this document and user
    scroll_result = client.scroll(
        collection_name=DOCUMENTS_COLLECTION,
        scroll_filter=Filter(
            must=[
                FieldCondition(key="document_id", match=MatchValue(value=document_id)),
                FieldCondition(key="user_id", match=MatchValue(value=user_id))
            ]
        ),
        with_payload=False  # We only need IDs
    )
    
    point_ids = [point.id for point in scroll_result[0]]
    
    if not point_ids:
        return False
    
    # Delete all points for this document
    client.delete(
        collection_name=DOCUMENTS_COLLECTION,
        points_selector=point_ids
    )
    
    return True 
