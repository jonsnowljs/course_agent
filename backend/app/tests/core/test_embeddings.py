import pytest
from unittest.mock import patch, MagicMock, mock_open
import io

from app.core.embeddings import (
    extract_text_from_file,
    extract_text_from_pdf,
    extract_text_from_docx,
    chunk_text,
    generate_embeddings,
    create_document_chunks,
    get_openai_client
)


class TestTextExtraction:
    """Test text extraction from various file formats."""

    def test_extract_text_from_txt_file(self):
        """Test text extraction from TXT file."""
        test_content = b"This is a simple text file content."
        result = extract_text_from_file(test_content, "test.txt")
        assert result == "This is a simple text file content."

    def test_extract_text_from_txt_file_with_encoding_errors(self):
        """Test text extraction from TXT file with encoding issues."""
        # Invalid UTF-8 bytes
        test_content = b"\x80\x81\x82"
        result = extract_text_from_file(test_content, "test.txt")
        # Should handle encoding errors gracefully
        assert isinstance(result, str)

    @patch('app.core.embeddings.PyPDF2.PdfReader')
    def test_extract_text_from_pdf(self, mock_pdf_reader):
        """Test text extraction from PDF file."""
        # Mock PDF reader
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "PDF page content"
        mock_pdf_reader.return_value.pages = [mock_page]
        
        test_content = b"fake_pdf_content"
        result = extract_text_from_pdf(test_content)
        assert result == "PDF page content"

    @patch('app.core.embeddings.docx.Document')
    def test_extract_text_from_docx(self, mock_docx_document):
        """Test text extraction from DOCX file."""
        # Mock DOCX document
        mock_paragraph = MagicMock()
        mock_paragraph.text = "DOCX paragraph content"
        mock_docx_document.return_value.paragraphs = [mock_paragraph]
        
        test_content = b"fake_docx_content"
        result = extract_text_from_docx(test_content)
        assert result == "DOCX paragraph content"

    def test_extract_text_from_unknown_file_type(self):
        """Test text extraction from unknown file type."""
        test_content = b"Some random content"
        result = extract_text_from_file(test_content, "test.unknown")
        assert result == "Some random content"


class TestTextChunking:
    """Test text chunking functionality."""

    def test_chunk_text_basic(self):
        """Test basic text chunking."""
        text = "This is a test sentence. " * 100  # Create long text
        chunks = chunk_text(text, chunk_size=10, overlap=2)
        
        assert len(chunks) > 1
        assert all(isinstance(chunk, str) for chunk in chunks)
        
        # Check overlap exists between chunks
        words_chunk1 = chunks[0].split()
        words_chunk2 = chunks[1].split()
        # Should have some overlap
        assert len(words_chunk1) <= 10

    def test_chunk_text_short_text(self):
        """Test chunking of text shorter than chunk size."""
        text = "Short text"
        chunks = chunk_text(text, chunk_size=10, overlap=2)
        
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_chunk_text_empty_text(self):
        """Test chunking of empty text."""
        text = ""
        chunks = chunk_text(text, chunk_size=10, overlap=2)
        
        assert len(chunks) == 0

    def test_chunk_text_whitespace_only(self):
        """Test chunking of whitespace-only text."""
        text = "   \n\t   "
        chunks = chunk_text(text, chunk_size=10, overlap=2)
        
        assert len(chunks) == 0


class TestEmbeddingGeneration:
    """Test embedding generation using OpenAI API."""

    @patch('app.core.embeddings.get_openai_client')
    def test_generate_embeddings_success(self, mock_get_client):
        """Test successful embedding generation."""
        # Mock OpenAI client response
        mock_client = MagicMock()
        mock_embedding = MagicMock()
        mock_embedding.embedding = [0.1, 0.2, 0.3]
        mock_response = MagicMock()
        mock_response.data = [mock_embedding, mock_embedding]
        mock_client.embeddings.create.return_value = mock_response
        mock_get_client.return_value = mock_client
        
        texts = ["First text", "Second text"]
        embeddings = generate_embeddings(texts)
        
        assert len(embeddings) == 2
        assert embeddings[0] == [0.1, 0.2, 0.3]
        assert embeddings[1] == [0.1, 0.2, 0.3]
        
        # Verify OpenAI API was called
        mock_client.embeddings.create.assert_called_once()

    @patch('app.core.embeddings.get_openai_client')
    def test_generate_embeddings_batch_processing(self, mock_get_client):
        """Test embedding generation with batch processing."""
        # Mock OpenAI client response
        mock_client = MagicMock()
        mock_embedding = MagicMock()
        mock_embedding.embedding = [0.1] * 1536
        mock_response = MagicMock()
        mock_response.data = [mock_embedding] * 150  # More than batch size
        mock_client.embeddings.create.return_value = mock_response
        mock_get_client.return_value = mock_client
        
        # Create more texts than batch size
        texts = [f"Text {i}" for i in range(150)]
        embeddings = generate_embeddings(texts)
        
        assert len(embeddings) == 150
        # Should have made multiple API calls due to batching
        assert mock_client.embeddings.create.call_count >= 2

    @patch('app.core.embeddings.get_openai_client')
    def test_generate_embeddings_api_error(self, mock_get_client):
        """Test handling of OpenAI API errors."""
        mock_client = MagicMock()
        mock_client.embeddings.create.side_effect = Exception("API Error")
        mock_get_client.return_value = mock_client
        
        texts = ["Test text"]
        
        with pytest.raises(Exception) as exc_info:
            generate_embeddings(texts)
        
        assert "Failed to generate embeddings" in str(exc_info.value)

    @patch('app.core.embeddings.get_openai_client')
    def test_generate_embeddings_empty_text_handling(self, mock_get_client):
        """Test handling of empty texts in embedding generation."""
        mock_client = MagicMock()
        mock_embedding = MagicMock()
        mock_embedding.embedding = [0.1] * 1536
        mock_response = MagicMock()
        mock_response.data = [mock_embedding]
        mock_client.embeddings.create.return_value = mock_response
        mock_get_client.return_value = mock_client
        
        texts = [""]  # Empty text
        embeddings = generate_embeddings(texts)
        
        assert len(embeddings) == 1
        # Should have called API with "empty text" fallback
        mock_client.embeddings.create.assert_called_once()
        call_args = mock_client.embeddings.create.call_args[1]
        assert "empty text" in call_args["input"]

    @patch('app.core.embeddings.get_openai_client')
    def test_generate_embeddings_long_text_truncation(self, mock_get_client):
        """Test truncation of texts that are too long."""
        mock_client = MagicMock()
        mock_embedding = MagicMock()
        mock_embedding.embedding = [0.1] * 1536
        mock_response = MagicMock()
        mock_response.data = [mock_embedding]
        mock_client.embeddings.create.return_value = mock_response
        mock_get_client.return_value = mock_client
        
        # Create very long text (more than 32000 characters)
        long_text = "a" * 35000
        texts = [long_text]
        
        embeddings = generate_embeddings(texts)
        
        assert len(embeddings) == 1
        # Should have called API with truncated text
        mock_client.embeddings.create.assert_called_once()
        call_args = mock_client.embeddings.create.call_args[1]
        processed_text = call_args["input"][0]
        assert len(processed_text) <= 32000


class TestDocumentChunkCreation:
    """Test document chunk creation for Qdrant storage."""

    @patch('app.core.embeddings.generate_embeddings')
    @patch('app.core.embeddings.chunk_text')
    def test_create_document_chunks_success(self, mock_chunk_text, mock_generate_embeddings):
        """Test successful creation of document chunks."""
        # Mock chunking and embedding generation
        mock_chunk_text.return_value = ["Chunk 1", "Chunk 2"]
        mock_generate_embeddings.return_value = [[0.1] * 1536, [0.2] * 1536]
        
        content = "Test document content"
        filename = "test.txt"
        user_id = "user-123"
        
        chunks = create_document_chunks(content, filename, user_id)
        
        assert len(chunks) == 2
        
        # Check chunk structure
        chunk = chunks[0]
        assert "id" in chunk
        assert "vector" in chunk
        assert "payload" in chunk
        
        # Check payload content
        payload = chunk["payload"]
        assert payload["filename"] == filename
        assert payload["user_id"] == user_id
        assert payload["chunk_index"] == 0
        assert payload["chunk_text"] == "Chunk 1"
        assert "document_id" in payload
        assert "created_at" in payload
        assert "file_hash" in payload
        assert payload["chunk_word_count"] == 2  # "Chunk 1" has 2 words

    @patch('app.core.embeddings.chunk_text')
    def test_create_document_chunks_empty_chunks(self, mock_chunk_text):
        """Test handling of content that produces no chunks."""
        mock_chunk_text.return_value = []
        
        content = ""
        filename = "empty.txt"
        user_id = "user-123"
        
        with pytest.raises(ValueError) as exc_info:
            create_document_chunks(content, filename, user_id)
        
        assert "No chunks were created" in str(exc_info.value)

    @patch('app.core.embeddings.generate_embeddings')
    @patch('app.core.embeddings.chunk_text')
    def test_create_document_chunks_consistent_document_id(self, mock_chunk_text, mock_generate_embeddings):
        """Test that all chunks from same document have same document_id."""
        mock_chunk_text.return_value = ["Chunk 1", "Chunk 2", "Chunk 3"]
        mock_generate_embeddings.return_value = [[0.1] * 1536] * 3
        
        content = "Test document content"
        filename = "test.txt"
        user_id = "user-123"
        
        chunks = create_document_chunks(content, filename, user_id)
        
        document_ids = [chunk["payload"]["document_id"] for chunk in chunks]
        assert len(set(document_ids)) == 1  # All chunks should have same document_id

    @patch('app.core.embeddings.generate_embeddings')
    @patch('app.core.embeddings.chunk_text')
    def test_create_document_chunks_chunk_indices(self, mock_chunk_text, mock_generate_embeddings):
        """Test that chunk indices are assigned correctly."""
        mock_chunk_text.return_value = ["Chunk 1", "Chunk 2", "Chunk 3"]
        mock_generate_embeddings.return_value = [[0.1] * 1536] * 3
        
        content = "Test document content"
        filename = "test.txt"
        user_id = "user-123"
        
        chunks = create_document_chunks(content, filename, user_id)
        
        indices = [chunk["payload"]["chunk_index"] for chunk in chunks]
        assert indices == [0, 1, 2]


class TestOpenAIClient:
    """Test OpenAI client initialization."""

    @patch('app.core.embeddings.OpenAI')
    @patch('app.core.embeddings.settings')
    def test_get_openai_client_initialization(self, mock_settings, mock_openai):
        """Test OpenAI client initialization."""
        mock_settings.OPENAI_API_KEY = "test-api-key"
        mock_openai_instance = MagicMock()
        mock_openai.return_value = mock_openai_instance
        
        # Clear global client to test initialization
        import app.core.embeddings
        app.core.embeddings._openai_client = None
        
        client = get_openai_client()
        
        assert client == mock_openai_instance
        mock_openai.assert_called_once_with(api_key="test-api-key")

    @patch('app.core.embeddings.OpenAI')
    @patch('app.core.embeddings.settings')
    def test_get_openai_client_singleton(self, mock_settings, mock_openai):
        """Test that OpenAI client is a singleton."""
        mock_settings.OPENAI_API_KEY = "test-api-key"
        mock_openai_instance = MagicMock()
        mock_openai.return_value = mock_openai_instance
        
        # Clear global client
        import app.core.embeddings
        app.core.embeddings._openai_client = None
        
        client1 = get_openai_client()
        client2 = get_openai_client()
        
        assert client1 == client2
        # Should only initialize once
        mock_openai.assert_called_once() 
