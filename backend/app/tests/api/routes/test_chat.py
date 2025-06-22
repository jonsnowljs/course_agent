import pytest
import json
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from app.tests.utils.user import create_random_user


class TestChatHealthEndpoint:
    """Test chat health check functionality."""

    def test_chat_health_success(self, client: TestClient):
        """Test successful health check."""
        response = client.get(f"{settings.API_V1_STR}/chat/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "openai_configured" in data
        assert data["status"] == "healthy"

    @patch('app.api.routes.chat.get_openai_client')
    def test_chat_health_with_openai_error(self, mock_openai_client, client: TestClient):
        """Test health check when OpenAI client fails."""
        mock_openai_client.side_effect = Exception("OpenAI connection failed")
        
        response = client.get(f"{settings.API_V1_STR}/chat/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "unhealthy"
        assert "error" in data


class TestChatMessage:
    """Test chat message functionality."""

    @patch('app.api.routes.chat.search_relevant_context')
    @patch('app.api.routes.chat.generate_chat_response')
    def test_chat_message_success_non_streaming(
        self,
        mock_generate_response,
        mock_search_context,
        client: TestClient,
        superuser_token_headers: dict[str, str]
    ):
        """Test successful non-streaming chat message."""
        # Mock context search
        mock_context = [
            {
                "filename": "test.txt",
                "chunk_text": "This is test content",
                "score": 0.95,
                "document_id": "doc-123",
                "chunk_index": 0,
                "created_at": "2024-01-01T00:00:00"
            }
        ]
        mock_search_context.return_value = mock_context

        # Mock response generation
        mock_generate_response.return_value = iter(["This is a test response."])

        chat_data = {
            "message": "What is the test content about?",
            "context_limit": 5,
            "stream": False
        }

        response = client.post(
            f"{settings.API_V1_STR}/chat/message",
            headers=superuser_token_headers,
            json=chat_data
        )

        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "context_used" in data
        assert "message_id" in data
        assert "timestamp" in data
        assert data["response"] == "This is a test response."
        assert len(data["context_used"]) == 1

    @patch('app.api.routes.chat.search_relevant_context')
    @patch('app.api.routes.chat.generate_chat_response')
    def test_chat_message_success_streaming(
        self,
        mock_generate_response,
        mock_search_context,
        client: TestClient,
        superuser_token_headers: dict[str, str]
    ):
        """Test successful streaming chat message."""
        # Mock context search
        mock_context = [
            {
                "filename": "test.txt",
                "chunk_text": "This is test content",
                "score": 0.95,
                "document_id": "doc-123",
                "chunk_index": 0,
                "created_at": "2024-01-01T00:00:00"
            }
        ]
        mock_search_context.return_value = mock_context

        # Mock response generation
        mock_generate_response.return_value = iter(["This ", "is ", "a ", "test."])

        chat_data = {
            "message": "What is the test content about?",
            "context_limit": 5,
            "stream": True
        }

        response = client.post(
            f"{settings.API_V1_STR}/chat/message",
            headers=superuser_token_headers,
            json=chat_data
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream"

        # Parse streaming response
        content = response.content.decode('utf-8')
        lines = [line for line in content.split('\n') if line.startswith('data: ')]
        
        # Should have metadata, content chunks, and completion
        assert len(lines) >= 3  # At least metadata, some content, and completion
        
        # Check metadata
        metadata = json.loads(lines[0][6:])  # Remove 'data: ' prefix
        assert metadata["type"] == "metadata"
        assert "message_id" in metadata
        assert "context_used" in metadata

        # Check completion
        completion = json.loads(lines[-1][6:])
        assert completion["type"] == "complete"
        assert completion["full_response"] == "This is a test."

    def test_chat_message_empty_message(
        self,
        client: TestClient,
        superuser_token_headers: dict[str, str]
    ):
        """Test chat with empty message."""
        chat_data = {
            "message": "",
            "stream": False
        }

        response = client.post(
            f"{settings.API_V1_STR}/chat/message",
            headers=superuser_token_headers,
            json=chat_data
        )

        assert response.status_code == 400
        assert "Message cannot be empty" in response.json()["detail"]

    def test_chat_message_whitespace_only(
        self,
        client: TestClient,
        superuser_token_headers: dict[str, str]
    ):
        """Test chat with whitespace-only message."""
        chat_data = {
            "message": "   \n\t   ",
            "stream": False
        }

        response = client.post(
            f"{settings.API_V1_STR}/chat/message",
            headers=superuser_token_headers,
            json=chat_data
        )

        assert response.status_code == 400
        assert "Message cannot be empty" in response.json()["detail"]

    def test_chat_message_without_authentication(self, client: TestClient):
        """Test chat without authentication."""
        chat_data = {
            "message": "Hello",
            "stream": False
        }

        response = client.post(
            f"{settings.API_V1_STR}/chat/message",
            json=chat_data
        )

        assert response.status_code == 401

    @patch('app.api.routes.chat.search_relevant_context')
    @patch('app.api.routes.chat.generate_chat_response')
    def test_chat_message_with_no_context(
        self,
        mock_generate_response,
        mock_search_context,
        client: TestClient,
        superuser_token_headers: dict[str, str]
    ):
        """Test chat when no documents are found."""
        # Mock empty context
        mock_search_context.return_value = []
        mock_generate_response.return_value = iter(["I don't have any documents to reference."])

        chat_data = {
            "message": "What documents do I have?",
            "stream": False
        }

        response = client.post(
            f"{settings.API_V1_STR}/chat/message",
            headers=superuser_token_headers,
            json=chat_data
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["context_used"]) == 0
        assert "documents" in data["response"].lower()

    @patch('app.api.routes.chat.search_relevant_context')
    @patch('app.api.routes.chat.generate_chat_response')
    def test_chat_message_with_generation_error(
        self,
        mock_generate_response,
        mock_search_context,
        client: TestClient,
        superuser_token_headers: dict[str, str]
    ):
        """Test chat when response generation fails."""
        mock_search_context.return_value = []
        mock_generate_response.return_value = iter(["Error generating response: OpenAI API failed"])

        chat_data = {
            "message": "Hello",
            "stream": False
        }

        response = client.post(
            f"{settings.API_V1_STR}/chat/message",
            headers=superuser_token_headers,
            json=chat_data
        )

        assert response.status_code == 200
        data = response.json()
        assert "Error generating response" in data["response"]


class TestChatHelperFunctions:
    """Test chat helper functions."""

    @patch('app.api.routes.chat.search_documents')
    def test_search_relevant_context_success(self, mock_search_documents):
        """Test successful context search."""
        from app.api.routes.chat import search_relevant_context
        
        mock_results = [
            {
                "filename": "doc1.txt",
                "chunk_text": "Content 1",
                "score": 0.95,
                "document_id": "doc-1",
                "chunk_index": 0,
                "created_at": "2024-01-01T00:00:00"
            }
        ]
        mock_search_documents.return_value = mock_results

        result = search_relevant_context("test query", "user-123", 5)
        
        assert result == mock_results
        mock_search_documents.assert_called_once_with("test query", "user-123", 5)

    @patch('app.api.routes.chat.search_documents')
    def test_search_relevant_context_with_error(self, mock_search_documents):
        """Test context search with error."""
        from app.api.routes.chat import search_relevant_context
        
        mock_search_documents.side_effect = Exception("Search failed")

        result = search_relevant_context("test query", "user-123", 5)
        
        assert result == []

    def test_build_system_prompt_with_context(self):
        """Test system prompt building with context."""
        from app.api.routes.chat import build_system_prompt
        
        context = [
            {
                "filename": "doc1.txt",
                "chunk_text": "This is document 1 content"
            },
            {
                "filename": "doc2.txt", 
                "chunk_text": "This is document 2 content"
            }
        ]

        prompt = build_system_prompt(context)
        
        assert "helpful AI assistant with access to the user's uploaded documents" in prompt
        assert "doc1.txt" in prompt
        assert "doc2.txt" in prompt
        assert "This is document 1 content" in prompt
        assert "This is document 2 content" in prompt

    def test_build_system_prompt_without_context(self):
        """Test system prompt building without context."""
        from app.api.routes.chat import build_system_prompt
        
        prompt = build_system_prompt([])
        
        assert "hasn't uploaded any documents yet" in prompt
        assert "general knowledge" in prompt

    @patch('app.api.routes.chat.get_openai_client')
    def test_generate_chat_response_streaming(self, mock_get_client):
        """Test chat response generation with streaming."""
        from app.api.routes.chat import generate_chat_response
        
        # Mock OpenAI streaming response
        mock_chunk = MagicMock()
        mock_chunk.choices = [MagicMock()]
        mock_chunk.choices[0].delta.content = "Hello"
        
        mock_response = [mock_chunk]
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        context = [{"filename": "test.txt", "chunk_text": "Test content"}]
        
        result = list(generate_chat_response("Hello", context, stream=True))
        
        assert result == ["Hello"]
        mock_client.chat.completions.create.assert_called_once()
        call_args = mock_client.chat.completions.create.call_args[1]
        assert call_args["stream"] is True
        assert call_args["model"] == "gpt-4o-mini"

    @patch('app.api.routes.chat.get_openai_client')
    def test_generate_chat_response_non_streaming(self, mock_get_client):
        """Test chat response generation without streaming."""
        from app.api.routes.chat import generate_chat_response
        
        # Mock OpenAI non-streaming response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Complete response"
        
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        context = []
        
        result = list(generate_chat_response("Hello", context, stream=False))
        
        assert result == ["Complete response"]
        mock_client.chat.completions.create.assert_called_once()
        call_args = mock_client.chat.completions.create.call_args[1]
        assert "stream" not in call_args or call_args["stream"] is False

    @patch('app.api.routes.chat.get_openai_client')
    def test_generate_chat_response_with_error(self, mock_get_client):
        """Test chat response generation with OpenAI error."""
        from app.api.routes.chat import generate_chat_response
        
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("OpenAI API error")
        mock_get_client.return_value = mock_client

        result = list(generate_chat_response("Hello", [], stream=False))
        
        assert len(result) == 1
        assert "Error generating response" in result[0]


class TestChatIntegration:
    """Integration tests for chat functionality."""

    @patch('app.api.routes.chat.get_openai_client')
    @patch('app.core.qdrant_service.get_qdrant_client')
    def test_full_chat_workflow_with_documents(
        self,
        mock_qdrant_client,
        mock_openai_client,
        client: TestClient,
        normal_user_token_headers: dict[str, str]
    ):
        """Test complete chat workflow with uploaded documents."""
        # Mock Qdrant search results
        mock_search_result = MagicMock()
        mock_search_result.id = "chunk-1"
        mock_search_result.score = 0.95
        mock_search_result.payload = {
            "filename": "test.txt",
            "chunk_text": "Python is a programming language",
            "document_id": "doc-123",
            "chunk_index": 0,
            "created_at": "2024-01-01T00:00:00"
        }

        mock_qdrant_client.return_value.get_collection.return_value = None
        mock_qdrant_client.return_value.search.return_value = [mock_search_result]

        # Mock OpenAI embedding for search
        mock_embedding_response = MagicMock()
        mock_embedding_response.data = [MagicMock(embedding=[0.1] * 1536)]
        
        # Mock OpenAI chat response
        mock_chat_response = MagicMock()
        mock_chat_response.choices = [MagicMock()]
        mock_chat_response.choices[0].message.content = "Python is indeed a programming language, as mentioned in your document test.txt."

        mock_openai_client.return_value.embeddings.create.return_value = mock_embedding_response
        mock_openai_client.return_value.chat.completions.create.return_value = mock_chat_response

        # Send chat message
        chat_data = {
            "message": "What is Python?",
            "context_limit": 5,
            "stream": False
        }

        response = client.post(
            f"{settings.API_V1_STR}/chat/message",
            headers=normal_user_token_headers,
            json=chat_data
        )

        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "response" in data
        assert "context_used" in data
        assert "message_id" in data
        assert "timestamp" in data
        
        # Verify context was found and used
        assert len(data["context_used"]) == 1
        assert data["context_used"][0]["filename"] == "test.txt"
        assert data["context_used"][0]["chunk_text"] == "Python is a programming language"
        
        # Verify response references the document
        assert "Python" in data["response"]

    @patch('app.api.routes.chat.get_openai_client')
    @patch('app.core.qdrant_service.get_qdrant_client')
    def test_chat_without_documents(
        self,
        mock_qdrant_client,
        mock_openai_client,
        client: TestClient,
        normal_user_token_headers: dict[str, str]
    ):
        """Test chat when user has no documents."""
        # Mock empty search results
        mock_qdrant_client.return_value.get_collection.return_value = None
        mock_qdrant_client.return_value.search.return_value = []

        # Mock OpenAI embedding for search
        mock_embedding_response = MagicMock()
        mock_embedding_response.data = [MagicMock(embedding=[0.1] * 1536)]
        
        # Mock OpenAI chat response for no documents scenario
        mock_chat_response = MagicMock()
        mock_chat_response.choices = [MagicMock()]
        mock_chat_response.choices[0].message.content = "I don't have access to any of your documents yet. Please upload some documents first."

        mock_openai_client.return_value.embeddings.create.return_value = mock_embedding_response
        mock_openai_client.return_value.chat.completions.create.return_value = mock_chat_response

        chat_data = {
            "message": "What documents do I have?",
            "stream": False
        }

        response = client.post(
            f"{settings.API_V1_STR}/chat/message",
            headers=normal_user_token_headers,
            json=chat_data
        )

        assert response.status_code == 200
        data = response.json()
        
        # Verify no context was used
        assert len(data["context_used"]) == 0
        
        # Verify response indicates no documents
        assert "documents" in data["response"].lower() 
