import pytest
import io
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from app.tests.utils.user import create_random_user


class TestDocumentUpload:
    """Test document upload functionality."""

    @patch('app.core.embeddings.get_openai_client')
    @patch('app.core.qdrant_service.get_qdrant_client')
    def test_upload_text_document_success(
        self,
        mock_qdrant_client,
        mock_openai_client,
        client: TestClient,
        superuser_token_headers: dict[str, str]
    ):
        """Test successful upload of a text document."""
        # Mock OpenAI response
        mock_embedding_response = MagicMock()
        mock_embedding_response.data = [MagicMock(embedding=[0.1] * 1536)]
        mock_openai_client.return_value.embeddings.create.return_value = mock_embedding_response
        
        # Mock Qdrant client
        mock_qdrant_client.return_value.get_collection.side_effect = Exception("Collection not found")
        mock_qdrant_client.return_value.create_collection.return_value = None
        mock_qdrant_client.return_value.upsert.return_value = None

        # Create test file
        test_content = "This is a test document with some content for testing."
        files = {"file": ("test.txt", test_content.encode(), "text/plain")}

        response = client.post(
            f"{settings.API_V1_STR}/documents/upload/",
            headers=superuser_token_headers,
            files=files
        )

        assert response.status_code == 200
        data = response.json()
        assert "document_id" in data
        assert data["filename"] == "test.txt"
        assert data["chunks_count"] >= 1
        assert data["total_words"] > 0
        assert data["message"] == "Document uploaded and processed successfully"

    @patch('app.core.embeddings.get_openai_client')
    @patch('app.core.qdrant_service.get_qdrant_client')
    def test_upload_pdf_document_success(
        self,
        mock_qdrant_client,
        mock_openai_client,
        client: TestClient,
        superuser_token_headers: dict[str, str]
    ):
        """Test successful upload of a PDF document."""
        # Mock OpenAI response
        mock_embedding_response = MagicMock()
        mock_embedding_response.data = [MagicMock(embedding=[0.1] * 1536)]
        mock_openai_client.return_value.embeddings.create.return_value = mock_embedding_response
        
        # Mock Qdrant client
        mock_qdrant_client.return_value.get_collection.side_effect = Exception("Collection not found")
        mock_qdrant_client.return_value.create_collection.return_value = None
        mock_qdrant_client.return_value.upsert.return_value = None

        # Mock PDF extraction (since we don't want to create a real PDF)
        with patch('app.core.embeddings.extract_text_from_pdf') as mock_pdf_extract:
            mock_pdf_extract.return_value = "This is extracted PDF content."
            
            files = {"file": ("test.pdf", b"fake_pdf_content", "application/pdf")}

            response = client.post(
                f"{settings.API_V1_STR}/documents/upload/",
                headers=superuser_token_headers,
                files=files
            )

            assert response.status_code == 200
            data = response.json()
            assert data["filename"] == "test.pdf"

    def test_upload_unsupported_file_type(
        self,
        client: TestClient,
        superuser_token_headers: dict[str, str]
    ):
        """Test upload of unsupported file type."""
        files = {"file": ("test.exe", b"fake_content", "application/x-executable")}

        response = client.post(
            f"{settings.API_V1_STR}/documents/upload/",
            headers=superuser_token_headers,
            files=files
        )

        assert response.status_code == 400
        assert "Unsupported file type" in response.json()["detail"]

    def test_upload_large_file(
        self,
        client: TestClient,
        superuser_token_headers: dict[str, str]
    ):
        """Test upload of file that exceeds size limit."""
        # Create a file larger than 10MB
        large_content = b"a" * (11 * 1024 * 1024)  # 11MB
        files = {"file": ("large.txt", large_content, "text/plain")}

        response = client.post(
            f"{settings.API_V1_STR}/documents/upload/",
            headers=superuser_token_headers,
            files=files
        )

        assert response.status_code == 413
        assert "File too large" in response.json()["detail"]

    def test_upload_empty_file(
        self,
        client: TestClient,
        superuser_token_headers: dict[str, str]
    ):
        """Test upload of empty file."""
        files = {"file": ("empty.txt", b"", "text/plain")}

        response = client.post(
            f"{settings.API_V1_STR}/documents/upload/",
            headers=superuser_token_headers,
            files=files
        )

        assert response.status_code == 400
        assert "No text content could be extracted" in response.json()["detail"]

    def test_upload_without_authentication(self, client: TestClient):
        """Test upload without authentication."""
        files = {"file": ("test.txt", b"content", "text/plain")}

        response = client.post(
            f"{settings.API_V1_STR}/documents/upload/",
            files=files
        )

        assert response.status_code == 401


class TestDocumentSearch:
    """Test document search functionality."""

    @patch('app.core.embeddings.get_openai_client')
    @patch('app.core.qdrant_service.get_qdrant_client')
    def test_search_documents_success(
        self,
        mock_qdrant_client,
        mock_openai_client,
        client: TestClient,
        superuser_token_headers: dict[str, str]
    ):
        """Test successful document search."""
        # Mock OpenAI response
        mock_embedding_response = MagicMock()
        mock_embedding_response.data = [MagicMock(embedding=[0.1] * 1536)]
        mock_openai_client.return_value.embeddings.create.return_value = mock_embedding_response
        
        # Mock Qdrant search results
        mock_search_result = MagicMock()
        mock_search_result.id = "test-id"
        mock_search_result.score = 0.95
        mock_search_result.payload = {
            "filename": "test.txt",
            "chunk_text": "This is a test chunk",
            "document_id": "doc-123",
            "chunk_index": 0,
            "created_at": "2024-01-01T00:00:00"
        }
        
        mock_qdrant_client.return_value.get_collection.return_value = None
        mock_qdrant_client.return_value.search.return_value = [mock_search_result]

        search_data = {"query": "test content", "limit": 5}

        response = client.post(
            f"{settings.API_V1_STR}/documents/search/",
            headers=superuser_token_headers,
            json=search_data
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == "test-id"
        assert data[0]["score"] == 0.95
        assert data[0]["filename"] == "test.txt"

    def test_search_documents_without_authentication(self, client: TestClient):
        """Test search without authentication."""
        search_data = {"query": "test", "limit": 5}

        response = client.post(
            f"{settings.API_V1_STR}/documents/search/",
            json=search_data
        )

        assert response.status_code == 401

    @patch('app.core.embeddings.get_openai_client')
    def test_search_documents_openai_error(
        self,
        mock_openai_client,
        client: TestClient,
        superuser_token_headers: dict[str, str]
    ):
        """Test search when OpenAI API fails."""
        mock_openai_client.return_value.embeddings.create.side_effect = Exception("API Error")

        search_data = {"query": "test content", "limit": 5}

        response = client.post(
            f"{settings.API_V1_STR}/documents/search/",
            headers=superuser_token_headers,
            json=search_data
        )

        assert response.status_code == 500
        assert "Error searching documents" in response.json()["detail"]


class TestDocumentList:
    """Test document listing functionality."""

    @patch('app.core.qdrant_service.get_qdrant_client')
    def test_list_user_documents_success(
        self,
        mock_qdrant_client,
        client: TestClient,
        superuser_token_headers: dict[str, str]
    ):
        """Test successful listing of user documents."""
        # Mock Qdrant scroll results
        mock_point = MagicMock()
        mock_point.payload = {
            "document_id": "doc-123",
            "filename": "test.txt",
            "created_at": "2024-01-01T00:00:00",
            "chunk_word_count": 50
        }
        
        mock_qdrant_client.return_value.get_collection.return_value = None
        mock_qdrant_client.return_value.scroll.return_value = ([mock_point], None)

        response = client.get(
            f"{settings.API_V1_STR}/documents/",
            headers=superuser_token_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["document_id"] == "doc-123"
        assert data[0]["filename"] == "test.txt"
        assert data[0]["chunks_count"] == 1
        assert data[0]["total_words"] == 50

    def test_list_documents_without_authentication(self, client: TestClient):
        """Test listing without authentication."""
        response = client.get(f"{settings.API_V1_STR}/documents/")
        assert response.status_code == 401


class TestDocumentDelete:
    """Test document deletion functionality."""

    @patch('app.core.qdrant_service.get_qdrant_client')
    def test_delete_document_success(
        self,
        mock_qdrant_client,
        client: TestClient,
        superuser_token_headers: dict[str, str]
    ):
        """Test successful document deletion."""
        # Mock Qdrant operations
        mock_point = MagicMock()
        mock_point.id = "chunk-123"
        
        mock_qdrant_client.return_value.get_collection.return_value = None
        mock_qdrant_client.return_value.scroll.return_value = ([mock_point], None)
        mock_qdrant_client.return_value.delete.return_value = None

        response = client.delete(
            f"{settings.API_V1_STR}/documents/doc-123",
            headers=superuser_token_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Document deleted successfully"

    @patch('app.core.qdrant_service.get_qdrant_client')
    def test_delete_nonexistent_document(
        self,
        mock_qdrant_client,
        client: TestClient,
        superuser_token_headers: dict[str, str]
    ):
        """Test deletion of non-existent document."""
        # Mock empty scroll result
        mock_qdrant_client.return_value.get_collection.return_value = None
        mock_qdrant_client.return_value.scroll.return_value = ([], None)

        response = client.delete(
            f"{settings.API_V1_STR}/documents/nonexistent-doc",
            headers=superuser_token_headers
        )

        assert response.status_code == 404
        assert "Document not found" in response.json()["detail"]

    def test_delete_document_without_authentication(self, client: TestClient):
        """Test deletion without authentication."""
        response = client.delete(f"{settings.API_V1_STR}/documents/doc-123")
        assert response.status_code == 401


class TestDocumentStats:
    """Test document statistics functionality."""

    @patch('app.core.qdrant_service.get_qdrant_client')
    def test_get_document_stats_success(
        self,
        mock_qdrant_client,
        client: TestClient,
        superuser_token_headers: dict[str, str]
    ):
        """Test successful retrieval of document statistics."""
        # Mock multiple documents
        mock_points = []
        for i in range(3):
            mock_point = MagicMock()
            mock_point.payload = {
                "document_id": f"doc-{i}",
                "filename": f"test{i}.txt",
                "created_at": f"2024-01-0{i+1}T00:00:00",
                "chunk_word_count": 50 + i * 10
            }
            mock_points.append(mock_point)
        
        mock_qdrant_client.return_value.get_collection.return_value = None
        mock_qdrant_client.return_value.scroll.return_value = (mock_points, None)

        response = client.get(
            f"{settings.API_V1_STR}/documents/stats/",
            headers=superuser_token_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_documents"] == 3
        assert data["total_chunks"] == 3
        assert data["total_words"] == 180  # 50 + 60 + 70
        assert len(data["recent_documents"]) <= 5

    def test_get_document_stats_without_authentication(self, client: TestClient):
        """Test stats retrieval without authentication."""
        response = client.get(f"{settings.API_V1_STR}/documents/stats/")
        assert response.status_code == 401


class TestDocumentIntegration:
    """Integration tests for document workflow."""

    @patch('app.core.embeddings.get_openai_client')
    @patch('app.core.qdrant_service.get_qdrant_client')
    def test_full_document_workflow(
        self,
        mock_qdrant_client,
        mock_openai_client,
        client: TestClient,
        normal_user_token_headers: dict[str, str]
    ):
        """Test complete workflow: upload -> search -> list -> delete."""
        # Mock OpenAI response
        mock_embedding_response = MagicMock()
        mock_embedding_response.data = [MagicMock(embedding=[0.1] * 1536)]
        mock_openai_client.return_value.embeddings.create.return_value = mock_embedding_response
        
        # Mock Qdrant operations
        mock_qdrant_client.return_value.get_collection.side_effect = Exception("Collection not found")
        mock_qdrant_client.return_value.create_collection.return_value = None
        mock_qdrant_client.return_value.upsert.return_value = None

        # 1. Upload document
        test_content = "This is a comprehensive test document for integration testing."
        files = {"file": ("integration_test.txt", test_content.encode(), "text/plain")}

        upload_response = client.post(
            f"{settings.API_V1_STR}/documents/upload/",
            headers=normal_user_token_headers,
            files=files
        )

        assert upload_response.status_code == 200
        upload_data = upload_response.json()
        document_id = upload_data["document_id"]

        # 2. Search for the document (mock search results)
        mock_search_result = MagicMock()
        mock_search_result.id = "chunk-123"
        mock_search_result.score = 0.95
        mock_search_result.payload = {
            "filename": "integration_test.txt",
            "chunk_text": test_content,
            "document_id": document_id,
            "chunk_index": 0,
            "created_at": "2024-01-01T00:00:00"
        }
        mock_qdrant_client.return_value.search.return_value = [mock_search_result]

        search_response = client.post(
            f"{settings.API_V1_STR}/documents/search/",
            headers=normal_user_token_headers,
            json={"query": "comprehensive test", "limit": 5}
        )

        assert search_response.status_code == 200
        search_data = search_response.json()
        assert len(search_data) == 1
        assert search_data[0]["document_id"] == document_id

        # 3. List documents (mock list results)
        mock_point = MagicMock()
        mock_point.payload = {
            "document_id": document_id,
            "filename": "integration_test.txt",
            "created_at": "2024-01-01T00:00:00",
            "chunk_word_count": 50
        }
        mock_qdrant_client.return_value.scroll.return_value = ([mock_point], None)

        list_response = client.get(
            f"{settings.API_V1_STR}/documents/",
            headers=normal_user_token_headers
        )

        assert list_response.status_code == 200
        list_data = list_response.json()
        assert len(list_data) == 1
        assert list_data[0]["document_id"] == document_id

        # 4. Delete document (mock delete operation)
        mock_delete_point = MagicMock()
        mock_delete_point.id = "chunk-123"
        mock_qdrant_client.return_value.scroll.return_value = ([mock_delete_point], None)
        mock_qdrant_client.return_value.delete.return_value = None

        delete_response = client.delete(
            f"{settings.API_V1_STR}/documents/{document_id}",
            headers=normal_user_token_headers
        )

        assert delete_response.status_code == 200
        delete_data = delete_response.json()
        assert delete_data["message"] == "Document deleted successfully" 
