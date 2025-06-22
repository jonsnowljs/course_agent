import pytest
from unittest.mock import patch, MagicMock


class TestChatHelperFunctions:
    """Test chat helper functions in isolation."""

    def test_search_relevant_context_success(self):
        """Test successful context search."""
        from app.api.routes.chat import search_relevant_context
        
        with patch('app.api.routes.chat.search_documents') as mock_search:
            mock_results = [
                {
                    "id": "chunk-1",
                    "score": 0.95,
                    "filename": "test.txt",
                    "chunk_text": "This is test content",
                    "document_id": "doc-123",
                    "chunk_index": 0,
                    "created_at": "2024-01-01T00:00:00"
                }
            ]
            mock_search.return_value = mock_results

            result = search_relevant_context("test query", "user-123", 5)
            
            assert result == mock_results
            mock_search.assert_called_once_with("test query", "user-123", 5)

    def test_search_relevant_context_empty_results(self):
        """Test context search with no results."""
        from app.api.routes.chat import search_relevant_context
        
        with patch('app.api.routes.chat.search_documents') as mock_search:
            mock_search.return_value = []

            result = search_relevant_context("test query", "user-123", 5)
            
            assert result == []

    def test_search_relevant_context_with_exception(self):
        """Test context search handles exceptions gracefully."""
        from app.api.routes.chat import search_relevant_context
        
        with patch('app.api.routes.chat.search_documents') as mock_search:
            mock_search.side_effect = Exception("Database connection failed")

            result = search_relevant_context("test query", "user-123", 5)
            
            # Should return empty list when exception occurs
            assert result == []

    def test_build_system_prompt_with_context(self):
        """Test system prompt building with document context."""
        from app.api.routes.chat import build_system_prompt
        
        context = [
            {
                "filename": "document1.pdf",
                "chunk_text": "Machine learning is a subset of artificial intelligence."
            },
            {
                "filename": "document2.txt", 
                "chunk_text": "Python is a popular programming language for data science."
            }
        ]

        prompt = build_system_prompt(context)
        
        # Check that prompt includes assistant identity
        assert "helpful AI assistant" in prompt
        assert "access to the user's uploaded documents" in prompt
        
        # Check that document content is included
        assert "document1.pdf" in prompt
        assert "Machine learning is a subset of artificial intelligence." in prompt
        assert "document2.txt" in prompt
        assert "Python is a popular programming language" in prompt
        
        # Check that instructions are included
        assert "Answer based primarily on the provided context" in prompt
        assert "Reference specific documents when appropriate" in prompt

    def test_build_system_prompt_without_context(self):
        """Test system prompt building when no documents are available."""
        from app.api.routes.chat import build_system_prompt
        
        prompt = build_system_prompt([])
        
        # Should indicate no documents available
        assert "hasn't uploaded any documents yet" in prompt
        assert "answer based on your general knowledge" in prompt
        assert "upload documents for more specific" in prompt

    def test_build_system_prompt_with_empty_context(self):
        """Test system prompt building with empty context list."""
        from app.api.routes.chat import build_system_prompt
        
        prompt = build_system_prompt([])
        
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert "general knowledge" in prompt

    @patch('app.api.routes.chat.get_openai_client')
    def test_generate_chat_response_streaming_success(self, mock_get_client):
        """Test successful streaming response generation."""
        from app.api.routes.chat import generate_chat_response
        
        # Mock OpenAI streaming response
        mock_chunk1 = MagicMock()
        mock_chunk1.choices = [MagicMock()]
        mock_chunk1.choices[0].delta.content = "Hello "
        
        mock_chunk2 = MagicMock()
        mock_chunk2.choices = [MagicMock()]
        mock_chunk2.choices[0].delta.content = "world!"
        
        mock_chunk3 = MagicMock()
        mock_chunk3.choices = [MagicMock()]
        mock_chunk3.choices[0].delta.content = None  # End of stream
        
        mock_response = [mock_chunk1, mock_chunk2, mock_chunk3]
        
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        context = [{"filename": "test.txt", "chunk_text": "Test content"}]
        
        result = list(generate_chat_response("Hello", context, stream=True))
        
        assert result == ["Hello ", "world!"]
        
        # Verify OpenAI call
        mock_client.chat.completions.create.assert_called_once()
        call_args = mock_client.chat.completions.create.call_args[1]
        assert call_args["stream"] is True
        assert call_args["model"] == "gpt-4o-mini"
        assert call_args["temperature"] == 0.7
        assert call_args["max_tokens"] == 1000
        
        # Check messages structure
        messages = call_args["messages"]
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "Hello"

    @patch('app.api.routes.chat.get_openai_client')
    def test_generate_chat_response_non_streaming_success(self, mock_get_client):
        """Test successful non-streaming response generation."""
        from app.api.routes.chat import generate_chat_response
        
        # Mock OpenAI non-streaming response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "This is a complete response."
        
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        context = []
        
        result = list(generate_chat_response("Test", context, stream=False))
        
        assert result == ["This is a complete response."]
        
        # Verify OpenAI call
        mock_client.chat.completions.create.assert_called_once()
        call_args = mock_client.chat.completions.create.call_args[1]
        assert "stream" not in call_args or call_args["stream"] is False

    @patch('app.api.routes.chat.get_openai_client')
    def test_generate_chat_response_with_openai_exception(self, mock_get_client):
        """Test response generation handles OpenAI exceptions."""
        from app.api.routes.chat import generate_chat_response
        
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("OpenAI API rate limit exceeded")
        mock_get_client.return_value = mock_client

        result = list(generate_chat_response("Test", [], stream=False))
        
        assert len(result) == 1
        assert "Error generating response" in result[0]
        assert "OpenAI API rate limit exceeded" in result[0]

    @patch('app.api.routes.chat.get_openai_client')
    def test_generate_chat_response_with_empty_message(self, mock_get_client):
        """Test response generation with empty message."""
        from app.api.routes.chat import generate_chat_response
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "I'm not sure what you're asking about."
        
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        result = list(generate_chat_response("", [], stream=False))
        
        assert len(result) == 1
        # Should still work with empty message
        assert isinstance(result[0], str)

    @patch('app.api.routes.chat.get_openai_client')
    def test_generate_chat_response_with_none_content(self, mock_get_client):
        """Test response generation when OpenAI returns None content."""
        from app.api.routes.chat import generate_chat_response
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = None
        
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        result = list(generate_chat_response("Test", [], stream=False))
        
        assert result == [""]  # Should return empty string when content is None

    def test_build_system_prompt_with_special_characters(self):
        """Test system prompt building with special characters in content."""
        from app.api.routes.chat import build_system_prompt
        
        context = [
            {
                "filename": "special_chars.txt",
                "chunk_text": "Content with special chars: @#$%^&*(){}[]|\\:;\"'<>?,./`~"
            }
        ]

        prompt = build_system_prompt(context)
        
        # Should handle special characters without issues
        assert "special_chars.txt" in prompt
        assert "Content with special chars" in prompt
        assert isinstance(prompt, str)

    def test_build_system_prompt_with_long_content(self):
        """Test system prompt building with very long document content."""
        from app.api.routes.chat import build_system_prompt
        
        long_content = "A" * 10000  # Very long content
        context = [
            {
                "filename": "long_document.txt",
                "chunk_text": long_content
            }
        ]

        prompt = build_system_prompt(context)
        
        # Should handle long content
        assert "long_document.txt" in prompt
        assert long_content in prompt
        assert isinstance(prompt, str)

    def test_build_system_prompt_with_multiple_documents(self):
        """Test system prompt building with many documents."""
        from app.api.routes.chat import build_system_prompt
        
        context = []
        for i in range(10):
            context.append({
                "filename": f"document_{i}.txt",
                "chunk_text": f"Content of document {i}"
            })

        prompt = build_system_prompt(context)
        
        # Should include all documents
        for i in range(10):
            assert f"document_{i}.txt" in prompt
            assert f"Content of document {i}" in prompt

    @patch('app.api.routes.chat.get_openai_client')
    def test_generate_chat_response_model_parameters(self, mock_get_client):
        """Test that correct model parameters are used."""
        from app.api.routes.chat import generate_chat_response
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test response"
        
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        list(generate_chat_response("Test", [], stream=False))
        
        # Verify correct parameters
        call_args = mock_client.chat.completions.create.call_args[1]
        assert call_args["model"] == "gpt-4o-mini"
        assert call_args["temperature"] == 0.7
        assert call_args["max_tokens"] == 1000
        
        # Verify message structure
        messages = call_args["messages"]
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "Test"

    def test_build_system_prompt_context_formatting(self):
        """Test that context is properly formatted in system prompt."""
        from app.api.routes.chat import build_system_prompt
        
        context = [
            {
                "filename": "test1.txt",
                "chunk_text": "First document content"
            },
            {
                "filename": "test2.txt",
                "chunk_text": "Second document content"
            }
        ]

        prompt = build_system_prompt(context)
        
        # Check proper formatting
        assert "Document: test1.txt\nContent: First document content" in prompt
        assert "Document: test2.txt\nContent: Second document content" in prompt
        
        # Should have proper separation between documents
        context_section = prompt.split("CONTEXT FROM USER'S DOCUMENTS:")[1].split("Instructions:")[0]
        assert "test1.txt" in context_section
        assert "test2.txt" in context_section 
