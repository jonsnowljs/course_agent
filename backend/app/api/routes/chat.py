from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from typing import List, Dict, Any, Generator
from pydantic import BaseModel
import json
import asyncio
import uuid
from datetime import datetime

from app.api.deps import CurrentUser
from app.core.embeddings import get_openai_client
from app.core.qdrant_service import search_documents
from app.core.config import settings

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatMessage(BaseModel):
    message: str
    context_limit: int = 5  # Number of relevant document chunks to include
    stream: bool = True


class ChatResponse(BaseModel):
    response: str
    context_used: List[Dict[str, Any]]
    message_id: str
    timestamp: str


def search_relevant_context(query: str, user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Search for relevant document chunks to use as context."""
    try:
        return search_documents(query, user_id, limit)
    except Exception as e:
        print(f"Error searching context: {e}")
        return []


def build_system_prompt(context: List[Dict[str, Any]]) -> str:
    """Build system prompt with document context."""
    if not context:
        return """You are a helpful AI assistant. The user hasn't uploaded any documents yet, so answer based on your general knowledge. Let them know they can upload documents for more specific, contextual answers."""
    
    context_text = "\n\n".join([
        f"Document: {chunk['filename']}\nContent: {chunk['chunk_text']}"
        for chunk in context
    ])
    
    return f"""You are a helpful AI assistant with access to the user's uploaded documents. Use the following context from their documents to answer their questions accurately and specifically.

CONTEXT FROM USER'S DOCUMENTS:
{context_text}

Instructions:
- Answer based primarily on the provided context when relevant
- If the context doesn't contain relevant information, say so and provide general assistance
- Reference specific documents when appropriate
- Be concise but comprehensive
- If asked about something not in the documents, clarify that your answer is based on general knowledge"""


def generate_chat_response(
    message: str, 
    context: List[Dict[str, Any]], 
    stream: bool = True
) -> Generator[str, None, None]:
    """Generate streaming chat response using OpenAI."""
    client = get_openai_client()
    
    system_prompt = build_system_prompt(context)
    
    try:
        if stream:
            # Streaming response
            response = client.chat.completions.create(
                model="gpt-4o-mini",  # Using a more cost-effective model
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ],
                stream=True,
                temperature=0.7,
                max_tokens=1000
            )
            
            for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        else:
            # Non-streaming response
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            yield response.choices[0].message.content or ""
            
    except Exception as e:
        yield f"Error generating response: {str(e)}"


@router.post("/message")
async def chat_message(
    chat_request: ChatMessage,
    current_user: CurrentUser
) -> StreamingResponse:
    """
    Send a chat message and get a streaming response with document context.
    """
    if not chat_request.message.strip():
        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty"
        )
    
    # Search for relevant context from user's documents
    context = search_relevant_context(
        chat_request.message, 
        str(current_user.id), 
        chat_request.context_limit
    )
    
    message_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().isoformat()
    
    async def response_generator():
        """Generator for streaming response."""
        try:
            # Send metadata first
            metadata = {
                "type": "metadata",
                "message_id": message_id,
                "timestamp": timestamp,
                "context_used": context
            }
            yield f"data: {json.dumps(metadata)}\n\n"
            
            # Stream the response
            response_text = ""
            for chunk in generate_chat_response(
                chat_request.message, 
                context, 
                chat_request.stream
            ):
                response_text += chunk
                chunk_data = {
                    "type": "content",
                    "content": chunk,
                    "message_id": message_id
                }
                yield f"data: {json.dumps(chunk_data)}\n\n"
            
            # Send completion signal
            completion_data = {
                "type": "complete",
                "message_id": message_id,
                "full_response": response_text
            }
            yield f"data: {json.dumps(completion_data)}\n\n"
            
        except Exception as e:
            error_data = {
                "type": "error",
                "error": str(e),
                "message_id": message_id
            }
            yield f"data: {json.dumps(error_data)}\n\n"
    
    if chat_request.stream:
        return StreamingResponse(
            response_generator(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream",
            }
        )
    else:
        # For non-streaming, collect all chunks and return as JSON
        context = search_relevant_context(
            chat_request.message, 
            str(current_user.id), 
            chat_request.context_limit
        )
        
        response_text = ""
        for chunk in generate_chat_response(chat_request.message, context, False):
            response_text += chunk
        
        return ChatResponse(
            response=response_text,
            context_used=context,
            message_id=message_id,
            timestamp=timestamp
        )


@router.get("/health")
async def chat_health():
    """Health check for chat service."""
    try:
        client = get_openai_client()
        # Simple test to verify OpenAI connectivity
        return {"status": "healthy", "openai_configured": bool(settings.OPENAI_API_KEY)}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)} 
