import io
import PyPDF2
import docx
from typing import List, Dict, Any
import hashlib
import uuid
from datetime import datetime
from openai import OpenAI
from app.core.config import settings

# Global OpenAI client instance
_openai_client = None

def get_openai_client():
    """Get or create the OpenAI client instance."""
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
    return _openai_client

def extract_text_from_file(file_content: bytes, filename: str) -> str:
    """Extract text content from various file types."""
    if filename.lower().endswith('.pdf'):
        return extract_text_from_pdf(file_content)
    elif filename.lower().endswith('.docx'):
        return extract_text_from_docx(file_content)
    elif filename.lower().endswith('.txt'):
        return file_content.decode('utf-8', errors='ignore')
    else:
        # Try to decode as text for other file types
        try:
            return file_content.decode('utf-8')
        except UnicodeDecodeError:
            return file_content.decode('utf-8', errors='ignore')

def extract_text_from_pdf(file_content: bytes) -> str:
    """Extract text from PDF file."""
    pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
    text_content = []
    
    for page in pdf_reader.pages:
        text_content.append(page.extract_text())
    
    return '\n'.join(text_content)

def extract_text_from_docx(file_content: bytes) -> str:
    """Extract text from DOCX file."""
    doc = docx.Document(io.BytesIO(file_content))
    text_content = []
    
    for paragraph in doc.paragraphs:
        text_content.append(paragraph.text)
    
    return '\n'.join(text_content)

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """Split text into overlapping chunks."""
    words = text.split()
    chunks = []
    
    for i in range(0, len(words), chunk_size - overlap):
        chunk = ' '.join(words[i:i + chunk_size])
        if chunk.strip():
            chunks.append(chunk)
        
        # Break if we've reached the end
        if i + chunk_size >= len(words):
            break
    
    return chunks

def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """Generate embeddings for a list of texts using OpenAI's API."""
    client = get_openai_client()
    
    # Process texts in batches to avoid API limits
    batch_size = 100  # OpenAI allows up to 2048 inputs per request, but we'll be conservative
    all_embeddings = []
    
    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i:i + batch_size]
        
        # Clean texts to ensure they're not empty and within token limits
        cleaned_texts = []
        for text in batch_texts:
            # Remove excessive whitespace and ensure text is not empty
            cleaned_text = ' '.join(text.split())
            if cleaned_text:
                # Truncate if too long (OpenAI has a token limit)
                # Rough estimation: 1 token ≈ 4 characters for English text
                max_chars = 32000  # Conservative limit for text-embedding-3-small
                if len(cleaned_text) > max_chars:
                    cleaned_text = cleaned_text[:max_chars]
                cleaned_texts.append(cleaned_text)
            else:
                cleaned_texts.append("empty text")  # Fallback for empty texts
        
        try:
            response = client.embeddings.create(
                model=settings.OPENAI_EMBEDDING_MODEL,
                input=cleaned_texts
            )
            
            batch_embeddings = [embedding.embedding for embedding in response.data]
            all_embeddings.extend(batch_embeddings)
            
        except Exception as e:
            raise Exception(f"Failed to generate embeddings: {str(e)}")
    
    return all_embeddings

def create_document_chunks(content: str, filename: str, user_id: str) -> List[Dict[str, Any]]:
    """Create document chunks with metadata for Qdrant storage."""
    chunks = chunk_text(content)
    
    if not chunks:
        raise ValueError("No chunks were created from the document")
    
    embeddings = generate_embeddings(chunks)
    
    document_id = str(uuid.uuid4())
    file_hash = hashlib.md5(content.encode()).hexdigest()
    
    document_chunks = []
    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        chunk_data = {
            "id": str(uuid.uuid4()),
            "vector": embedding,
            "payload": {
                "document_id": document_id,
                "filename": filename,
                "user_id": user_id,
                "chunk_index": i,
                "chunk_text": chunk,
                "file_hash": file_hash,
                "created_at": datetime.utcnow().isoformat(),
                "chunk_word_count": len(chunk.split()),
                "embedding_model": settings.OPENAI_EMBEDDING_MODEL
            }
        }
        document_chunks.append(chunk_data)
    
    return document_chunks 
