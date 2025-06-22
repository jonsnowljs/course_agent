from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Query
from typing import List, Dict, Any
from pydantic import BaseModel

from app.api.deps import CurrentUser
from app.core.embeddings import extract_text_from_file
from app.core.qdrant_service import (
    store_document, 
    search_documents, 
    get_user_documents, 
    delete_document
)

router = APIRouter(prefix="/documents", tags=["documents"])


class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    chunks_count: int
    total_words: int
    message: str


class SearchRequest(BaseModel):
    query: str
    limit: int = 10


class SearchResult(BaseModel):
    id: str
    score: float
    filename: str
    chunk_text: str
    document_id: str
    chunk_index: int
    created_at: str


class UserDocument(BaseModel):
    document_id: str
    filename: str
    created_at: str
    chunks_count: int
    total_words: int


@router.post("/upload/", response_model=DocumentUploadResponse)
async def upload_document(
    current_user: CurrentUser,
    file: UploadFile = File(...)
) -> DocumentUploadResponse:
    """
    Upload and store a document in Qdrant.
    Supports: PDF, DOCX, TXT files
    """
    # Check file size (limit to 10MB)
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    file_content = await file.read()
    
    if len(file_content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="File too large. Maximum size is 10MB."
        )
    
    # Check file type
    allowed_extensions = {'.pdf', '.docx', '.txt', '.md', '.py', '.js', '.html', '.css'}
    file_extension = '.' + file.filename.split('.')[-1].lower() if '.' in file.filename else ''
    
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed types: {', '.join(allowed_extensions)}"
        )
    
    try:
        # Extract text content
        text_content = extract_text_from_file(file_content, file.filename)
        
        if not text_content.strip():
            raise HTTPException(
                status_code=400,
                detail="No text content could be extracted from the file."
            )
        
        # Store in Qdrant
        result = store_document(text_content, file.filename, str(current_user.id))
        
        return DocumentUploadResponse(
            **result,
            message="Document uploaded and processed successfully"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing document: {str(e)}"
        )


@router.post("/search/", response_model=List[SearchResult])
async def search_user_documents(
    search_request: SearchRequest,
    current_user: CurrentUser
) -> List[SearchResult]:
    """
    Search through user's documents using semantic similarity.
    """
    try:
        results = search_documents(
            query=search_request.query,
            user_id=str(current_user.id),
            limit=search_request.limit
        )
        return [SearchResult(**result) for result in results]
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error searching documents: {str(e)}"
        )


@router.get("/", response_model=List[UserDocument])
async def list_user_documents(
    current_user: CurrentUser,
    limit: int = Query(50, description="Maximum number of documents to return")
) -> List[UserDocument]:
    """
    List all documents uploaded by the current user.
    """
    try:
        documents = get_user_documents(str(current_user.id), limit=limit)
        return [UserDocument(**doc) for doc in documents]
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving documents: {str(e)}"
        )


@router.delete("/{document_id}")
async def delete_user_document(
    document_id: str,
    current_user: CurrentUser
) -> Dict[str, str]:
    """
    Delete a specific document and all its chunks.
    """
    try:
        success = delete_document(document_id, str(current_user.id))
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail="Document not found or you don't have permission to delete it."
            )
        
        return {"message": "Document deleted successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting document: {str(e)}"
        )


@router.get("/stats/")
async def get_user_document_stats(
    current_user: CurrentUser
) -> Dict[str, Any]:
    """
    Get statistics about user's documents.
    """
    try:
        documents = get_user_documents(str(current_user.id), limit=1000)
        
        stats = {
            "total_documents": len(documents),
            "total_chunks": sum(doc["chunks_count"] for doc in documents),
            "total_words": sum(doc["total_words"] for doc in documents),
            "recent_documents": sorted(
                documents, 
                key=lambda x: x["created_at"], 
                reverse=True
            )[:5]
        }
        
        return stats
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving document statistics: {str(e)}"
        ) 
