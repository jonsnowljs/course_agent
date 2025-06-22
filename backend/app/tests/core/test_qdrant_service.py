import pytest
from unittest.mock import patch, MagicMock

from app.core.qdrant_service import (
    ensure_collection_exists,
    store_document,
    search_documents,
    get_user_documents,
    delete_document,
    get_embedding_dimension,
    DOCUMENTS_COLLECTION
)


class TestEmbeddingDimension:
    """Test embedding dimension calculation."""

    @patch('app.core.qdrant_service.settings')
    def test_get_embedding_dimension_small_model(self, mock_settings):
        """Test dimension for text-embedding-3-small model."""
        mock_settings.OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
        dimension = get_embedding_dimension()
        assert dimension == 1536

    @patch('app.core.qdrant_service.settings')
    def test_get_embedding_dimension_large_model(self, mock_settings):
        """Test dimension for text-embedding-3-large model."""
        mock_settings.OPENAI_EMBEDDING_MODEL = "text-embedding-3-large"
        dimension = get_embedding_dimension()
        assert dimension == 3072

    @patch('app.core.qdrant_service.settings')
    def test_get_embedding_dimension_ada_model(self, mock_settings):
        """Test dimension for text-embedding-ada-002 model."""
        mock_settings.OPENAI_EMBEDDING_MODEL = "text-embedding-ada-002"
        dimension = get_embedding_dimension()
        assert dimension == 1536

    @patch('app.core.qdrant_service.settings')
    def test_get_embedding_dimension_unknown_model(self, mock_settings):
        """Test dimension for unknown model (should default to 1536)."""
        mock_settings.OPENAI_EMBEDDING_MODEL = "unknown-model"
        dimension = get_embedding_dimension()
        assert dimension == 1536


class TestCollectionManagement:
    """Test Qdrant collection management."""

    @patch('app.core.qdrant_service.get_qdrant_client')
    def test_ensure_collection_exists_already_exists(self, mock_get_client):
        """Test when collection already exists."""
        mock_client = MagicMock()
        mock_client.get_collection.return_value = MagicMock()  # Collection exists
        mock_get_client.return_value = mock_client

        ensure_collection_exists()

        mock_client.get_collection.assert_called_once_with(DOCUMENTS_COLLECTION)
        mock_client.create_collection.assert_not_called()

    @patch('app.core.qdrant_service.get_embedding_dimension')
    @patch('app.core.qdrant_service.get_qdrant_client')
    def test_ensure_collection_exists_create_new(self, mock_get_client, mock_get_dimension):
        """Test creating new collection when it doesn't exist."""
        mock_client = MagicMock()
        mock_client.get_collection.side_effect = Exception("Collection not found")
        mock_client.create_collection.return_value = None
        mock_get_client.return_value = mock_client
        mock_get_dimension.return_value = 1536

        ensure_collection_exists()

        mock_client.get_collection.assert_called_once_with(DOCUMENTS_COLLECTION)
        mock_client.create_collection.assert_called_once()
        # Verify create_collection was called with correct parameters
        call_args = mock_client.create_collection.call_args[1]
        assert call_args["collection_name"] == DOCUMENTS_COLLECTION
        assert call_args["vectors_config"].size == 1536


class TestDocumentStorage:
    """Test document storage functionality."""

    @patch('app.core.qdrant_service.ensure_collection_exists')
    @patch('app.core.qdrant_service.create_document_chunks')
    @patch('app.core.qdrant_service.get_qdrant_client')
    def test_store_document_success(self, mock_get_client, mock_create_chunks, mock_ensure_collection):
        """Test successful document storage."""
        # Mock document chunks
        mock_chunks = [
            {
                "id": "chunk-1",
                "vector": [0.1] * 1536,
                "payload": {
                    "document_id": "doc-123",
                    "filename": "test.txt",
                    "user_id": "user-123",
                    "chunk_text": "Test chunk 1",
                    "chunk_word_count": 3
                }
            },
            {
                "id": "chunk-2",
                "vector": [0.2] * 1536,
                "payload": {
                    "document_id": "doc-123",
                    "filename": "test.txt",
                    "user_id": "user-123",
                    "chunk_text": "Test chunk 2",
                    "chunk_word_count": 3
                }
            }
        ]
        mock_create_chunks.return_value = mock_chunks

        # Mock Qdrant client
        mock_client = MagicMock()
        mock_client.upsert.return_value = None
        mock_get_client.return_value = mock_client

        content = "Test document content"
        filename = "test.txt"
        user_id = "user-123"

        result = store_document(content, filename, user_id)

        # Verify the result
        assert result["document_id"] == "doc-123"
        assert result["filename"] == "test.txt"
        assert result["chunks_count"] == 2
        assert result["total_words"] == 6

        # Verify Qdrant operations
        mock_ensure_collection.assert_called_once()
        mock_create_chunks.assert_called_once_with(content, filename, user_id)
        mock_client.upsert.assert_called_once()

    @patch('app.core.qdrant_service.ensure_collection_exists')
    @patch('app.core.qdrant_service.create_document_chunks')
    def test_store_document_no_chunks(self, mock_create_chunks, mock_ensure_collection):
        """Test handling when no chunks are created."""
        mock_create_chunks.return_value = []

        content = ""
        filename = "empty.txt"
        user_id = "user-123"

        with pytest.raises(ValueError) as exc_info:
            store_document(content, filename, user_id)

        assert "No chunks were created" in str(exc_info.value)


class TestDocumentSearch:
    """Test document search functionality."""

    @patch('app.core.qdrant_service.ensure_collection_exists')
    @patch('app.core.qdrant_service.generate_embeddings')
    @patch('app.core.qdrant_service.get_qdrant_client')
    def test_search_documents_success(self, mock_get_client, mock_generate_embeddings, mock_ensure_collection):
        """Test successful document search."""
        # Mock embedding generation
        mock_generate_embeddings.return_value = [[0.1] * 1536]

        # Mock search results
        mock_search_result = MagicMock()
        mock_search_result.id = "chunk-123"
        mock_search_result.score = 0.95
        mock_search_result.payload = {
            "filename": "test.txt",
            "chunk_text": "Test content",
            "document_id": "doc-123",
            "chunk_index": 0,
            "created_at": "2024-01-01T00:00:00"
        }

        mock_client = MagicMock()
        mock_client.search.return_value = [mock_search_result]
        mock_get_client.return_value = mock_client

        query = "test query"
        user_id = "user-123"
        limit = 5

        results = search_documents(query, user_id, limit)

        # Verify results
        assert len(results) == 1
        result = results[0]
        assert result["id"] == "chunk-123"
        assert result["score"] == 0.95
        assert result["filename"] == "test.txt"
        assert result["chunk_text"] == "Test content"
        assert result["document_id"] == "doc-123"

        # Verify API calls
        mock_ensure_collection.assert_called_once()
        mock_generate_embeddings.assert_called_once_with([query])
        mock_client.search.assert_called_once()

        # Verify search parameters
        search_call = mock_client.search.call_args[1]
        assert search_call["collection_name"] == DOCUMENTS_COLLECTION
        assert search_call["query_vector"] == [0.1] * 1536
        assert search_call["limit"] == limit

    @patch('app.core.qdrant_service.ensure_collection_exists')
    @patch('app.core.qdrant_service.generate_embeddings')
    @patch('app.core.qdrant_service.get_qdrant_client')
    def test_search_documents_empty_results(self, mock_get_client, mock_generate_embeddings, mock_ensure_collection):
        """Test search with no results."""
        mock_generate_embeddings.return_value = [[0.1] * 1536]
        
        mock_client = MagicMock()
        mock_client.search.return_value = []
        mock_get_client.return_value = mock_client

        results = search_documents("query", "user-123", 5)

        assert results == []


class TestDocumentListing:
    """Test document listing functionality."""

    @patch('app.core.qdrant_service.ensure_collection_exists')
    @patch('app.core.qdrant_service.get_qdrant_client')
    def test_get_user_documents_success(self, mock_get_client, mock_ensure_collection):
        """Test successful retrieval of user documents."""
        # Mock scroll results with multiple chunks from different documents
        mock_points = []
        
        # Document 1 - 2 chunks
        for i in range(2):
            point = MagicMock()
            point.payload = {
                "document_id": "doc-1",
                "filename": "test1.txt",
                "created_at": "2024-01-01T00:00:00",
                "chunk_word_count": 50
            }
            mock_points.append(point)
        
        # Document 2 - 1 chunk
        point = MagicMock()
        point.payload = {
            "document_id": "doc-2",
            "filename": "test2.txt",
            "created_at": "2024-01-02T00:00:00",
            "chunk_word_count": 30
        }
        mock_points.append(point)

        mock_client = MagicMock()
        mock_client.scroll.return_value = (mock_points, None)
        mock_get_client.return_value = mock_client

        user_id = "user-123"
        limit = 50

        documents = get_user_documents(user_id, limit)

        # Should group chunks by document_id
        assert len(documents) == 2
        
        # Check document 1
        doc1 = next(doc for doc in documents if doc["document_id"] == "doc-1")
        assert doc1["filename"] == "test1.txt"
        assert doc1["chunks_count"] == 2
        assert doc1["total_words"] == 100  # 2 chunks * 50 words each

        # Check document 2
        doc2 = next(doc for doc in documents if doc["document_id"] == "doc-2")
        assert doc2["filename"] == "test2.txt"
        assert doc2["chunks_count"] == 1
        assert doc2["total_words"] == 30

        # Verify API calls
        mock_ensure_collection.assert_called_once()
        mock_client.scroll.assert_called_once()

    @patch('app.core.qdrant_service.ensure_collection_exists')
    @patch('app.core.qdrant_service.get_qdrant_client')
    def test_get_user_documents_no_documents(self, mock_get_client, mock_ensure_collection):
        """Test when user has no documents."""
        mock_client = MagicMock()
        mock_client.scroll.return_value = ([], None)
        mock_get_client.return_value = mock_client

        documents = get_user_documents("user-123", 50)

        assert documents == []


class TestDocumentDeletion:
    """Test document deletion functionality."""

    @patch('app.core.qdrant_service.ensure_collection_exists')
    @patch('app.core.qdrant_service.get_qdrant_client')
    def test_delete_document_success(self, mock_get_client, mock_ensure_collection):
        """Test successful document deletion."""
        # Mock points to be deleted
        mock_points = []
        for i in range(3):
            point = MagicMock()
            point.id = f"chunk-{i}"
            mock_points.append(point)

        mock_client = MagicMock()
        mock_client.scroll.return_value = (mock_points, None)
        mock_client.delete.return_value = None
        mock_get_client.return_value = mock_client

        document_id = "doc-123"
        user_id = "user-123"

        result = delete_document(document_id, user_id)

        assert result is True

        # Verify API calls
        mock_ensure_collection.assert_called_once()
        mock_client.scroll.assert_called_once()
        mock_client.delete.assert_called_once()

        # Verify deletion parameters
        delete_call = mock_client.delete.call_args[1]
        assert delete_call["collection_name"] == DOCUMENTS_COLLECTION
        assert delete_call["points_selector"] == ["chunk-0", "chunk-1", "chunk-2"]

    @patch('app.core.qdrant_service.ensure_collection_exists')
    @patch('app.core.qdrant_service.get_qdrant_client')
    def test_delete_document_not_found(self, mock_get_client, mock_ensure_collection):
        """Test deletion of non-existent document."""
        mock_client = MagicMock()
        mock_client.scroll.return_value = ([], None)  # No points found
        mock_get_client.return_value = mock_client

        document_id = "nonexistent-doc"
        user_id = "user-123"

        result = delete_document(document_id, user_id)

        assert result is False

        # Should not call delete when no points found
        mock_client.delete.assert_not_called()

    @patch('app.core.qdrant_service.ensure_collection_exists')
    @patch('app.core.qdrant_service.get_qdrant_client')
    def test_delete_document_user_isolation(self, mock_get_client, mock_ensure_collection):
        """Test that deletion respects user isolation."""
        mock_client = MagicMock()
        mock_client.scroll.return_value = ([], None)
        mock_get_client.return_value = mock_client

        document_id = "doc-123"
        user_id = "user-123"

        delete_document(document_id, user_id)

        # Verify scroll was called with proper filters
        scroll_call = mock_client.scroll.call_args[1]
        assert scroll_call["collection_name"] == DOCUMENTS_COLLECTION
        
        # Check that both document_id and user_id filters are applied
        filters = scroll_call["scroll_filter"].must
        assert len(filters) == 2
        
        # Should filter by both document_id and user_id
        filter_keys = [f.key for f in filters]
        assert "document_id" in filter_keys
        assert "user_id" in filter_keys


class TestIntegration:
    """Integration tests for Qdrant service operations."""

    @patch('app.core.qdrant_service.ensure_collection_exists')
    @patch('app.core.qdrant_service.create_document_chunks')
    @patch('app.core.qdrant_service.generate_embeddings')
    @patch('app.core.qdrant_service.get_qdrant_client')
    def test_store_search_delete_workflow(
        self, 
        mock_get_client, 
        mock_generate_embeddings, 
        mock_create_chunks, 
        mock_ensure_collection
    ):
        """Test complete workflow: store -> search -> delete."""
        # Setup mocks
        document_id = "doc-123"
        user_id = "user-123"
        
        # Mock document chunks
        mock_chunks = [{
            "id": "chunk-1",
            "vector": [0.1] * 1536,
            "payload": {
                "document_id": document_id,
                "filename": "test.txt",
                "user_id": user_id,
                "chunk_text": "Test content",
                "chunk_word_count": 2
            }
        }]
        mock_create_chunks.return_value = mock_chunks
        
        # Mock embeddings
        mock_generate_embeddings.return_value = [[0.1] * 1536]
        
        # Mock Qdrant client
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        # 1. Store document
        mock_client.upsert.return_value = None
        
        store_result = store_document("Test content", "test.txt", user_id)
        assert store_result["document_id"] == document_id
        
        # 2. Search documents
        mock_search_result = MagicMock()
        mock_search_result.id = "chunk-1"
        mock_search_result.score = 0.95
        mock_search_result.payload = mock_chunks[0]["payload"]
        mock_client.search.return_value = [mock_search_result]
        
        search_results = search_documents("test", user_id, 5)
        assert len(search_results) == 1
        assert search_results[0]["document_id"] == document_id
        
        # 3. Delete document
        mock_point = MagicMock()
        mock_point.id = "chunk-1"
        mock_client.scroll.return_value = ([mock_point], None)
        mock_client.delete.return_value = None
        
        delete_result = delete_document(document_id, user_id)
        assert delete_result is True
        
        # Verify all operations were called
        mock_client.upsert.assert_called_once()
        mock_client.search.assert_called_once()
        mock_client.delete.assert_called_once() 
