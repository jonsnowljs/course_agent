# Chat Functionality Testing Guide

This guide covers comprehensive testing for the new chat functionality that integrates with Qdrant for document-aware conversations.

## Overview

The chat feature provides:
- **Streaming chat responses** like ChatGPT
- **Document memory** using Qdrant vector search
- **Context-aware responses** based on uploaded documents
- **Real-time Server-Sent Events (SSE)** for streaming
- **RAG (Retrieval Augmented Generation)** capabilities

## Backend Testing

### 1. Integration Tests

Run the automated integration test:

```bash
cd backend
python test_chat_integration.py
```

This tests:
- ✅ Health endpoint
- ✅ Authentication
- ✅ Non-streaming chat
- ✅ Streaming chat  
- ✅ Edge cases (empty messages, long messages)
- ✅ Error handling

### 2. Unit Tests

Run pytest for detailed unit testing:

```bash
cd backend
pytest app/tests/api/routes/test_chat.py -v
pytest app/tests/core/test_chat_helpers.py -v
```

Test coverage includes:
- Chat endpoint functionality
- Search context retrieval
- System prompt building
- OpenAI response generation
- Error handling

### 3. Manual API Testing

#### Health Check
```bash
curl http://localhost:8000/api/v1/chat/health
```

#### Non-streaming Chat
```bash
curl -X POST http://localhost:8000/api/v1/chat/message \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What documents do I have?",
    "context_limit": 5,
    "stream": false
  }'
```

#### Streaming Chat
```bash
curl -X POST http://localhost:8000/api/v1/chat/message \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Tell me about my documents",
    "context_limit": 3,
    "stream": true
  }'
```

## Frontend Testing

### 1. Manual UI Testing

#### Prerequisites
1. Start the backend: `cd backend && python -m uvicorn app.main:app --reload`
2. Start the frontend: `cd frontend && npm run dev`
3. Navigate to `http://localhost:5173`
4. Login with credentials: `admin@example.com` / `password`

#### Test Cases

**Empty State (No Documents)**
1. Navigate to `/chat`
2. ✅ Should show "Upload Documents First" message
3. ✅ Input should be disabled
4. ✅ Send button should be disabled
5. ✅ Click "Upload Documents First" → should navigate to `/documents`

**With Documents**
1. Upload some documents first via `/documents`
2. Navigate to `/chat`
3. ✅ Input should be enabled
4. ✅ Should show placeholder "Ask a question about your documents..."

**Sending Messages**
1. Type a message: "What are the main topics in my documents?"
2. ✅ Send with Enter key or Send button
3. ✅ Should show user message in chat
4. ✅ Should show streaming response (text appearing progressively)
5. ✅ Input should be cleared after sending
6. ✅ Should show timestamp for both messages

**Context Display**
1. Send a message that should find relevant documents
2. ✅ Should show "Used X documents as context" button
3. ✅ Click to expand context details
4. ✅ Should show document names, match scores, and excerpts

**Edge Cases**
1. ✅ Empty message should keep Send button disabled
2. ✅ Whitespace-only message should keep Send button disabled
3. ✅ Shift+Enter should create new line, not send
4. ✅ Enter key should send message
5. ✅ Very long messages should be handled gracefully

**Error Handling**
1. ✅ Network errors should be handled gracefully
2. ✅ Should show loading state during requests
3. ✅ Should handle streaming interruptions

### 2. Accessibility Testing

**Keyboard Navigation**
1. ✅ Tab through all interactive elements
2. ✅ Enter key should send messages
3. ✅ Escape key should clear current message
4. ✅ Arrow keys should work in textarea

**Screen Reader Support**
1. ✅ All buttons have proper labels
2. ✅ Chat messages have proper semantic structure
3. ✅ Loading states are announced
4. ✅ Error messages are announced

## Performance Testing

### 1. Load Testing

Test with multiple concurrent requests:

```bash
# Install artillery for load testing
npm install -g artillery

# Create artillery config (artillery.yml):
config:
  target: 'http://localhost:8000'
  phases:
    - duration: 60
      arrivalRate: 5
scenarios:
  - name: "Chat API Load Test"
    requests:
      - post:
          url: "/api/v1/chat/message"
          headers:
            Authorization: "Bearer YOUR_TOKEN"
          json:
            message: "Test load message"
            stream: false

# Run load test
artillery run artillery.yml
```

### 2. Memory Testing

Monitor memory usage during streaming:

```bash
# Monitor backend memory
ps aux | grep uvicorn

# Monitor database connections
SELECT count(*) FROM pg_stat_activity;
```

### 3. Response Time Testing

Expected performance benchmarks:
- ✅ Context search: < 500ms
- ✅ Non-streaming response: < 3s
- ✅ Streaming first chunk: < 1s
- ✅ Full streaming response: < 10s

## Security Testing

### 1. Authentication Tests

```bash
# Test without token (should fail)
curl -X POST http://localhost:8000/api/v1/chat/message \
  -H "Content-Type: application/json" \
  -d '{"message": "test"}'

# Test with invalid token (should fail)
curl -X POST http://localhost:8000/api/v1/chat/message \
  -H "Authorization: Bearer invalid_token" \
  -H "Content-Type: application/json" \
  -d '{"message": "test"}'
```

### 2. Input Validation Tests

```bash
# Test with malicious input
curl -X POST http://localhost:8000/api/v1/chat/message \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "<script>alert(\"xss\")</script>"}'

# Test with very long input
curl -X POST http://localhost:8000/api/v1/chat/message \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "'$(python -c "print('A' * 100000)")'"}'
```

### 3. Rate Limiting

Test multiple rapid requests to ensure proper rate limiting.

## Document Context Testing

### 1. Test Document Upload and Search

1. Upload test documents with known content
2. Ask specific questions about that content
3. ✅ Verify relevant documents are found
4. ✅ Verify context is properly formatted
5. ✅ Verify responses reference specific documents

### 2. Test Different Document Types

Upload and test with:
- ✅ Text files (.txt)
- ✅ PDF documents (.pdf)
- ✅ Word documents (.docx)
- ✅ Markdown files (.md)

### 3. Test Context Accuracy

1. ✅ Relevant chunks should have high scores (>0.8)
2. ✅ Context should be properly attributed to source files
3. ✅ Multiple documents should be searchable
4. ✅ Search should work across different file types

## Monitoring and Observability

### 1. Logs to Monitor

```bash
# Backend logs
tail -f backend/logs/app.log

# Look for:
# - Chat request patterns
# - Context search performance
# - OpenAI API usage
# - Error patterns
```

### 2. Metrics to Track

- Request count and response times
- Context search accuracy
- OpenAI token usage
- Error rates
- User engagement (messages per session)

## Troubleshooting Common Issues

### 1. OpenAI API Issues

**Problem**: "OpenAI API error"
**Solution**: 
- Check `OPENAI_API_KEY` environment variable
- Verify API key has sufficient credits
- Check OpenAI API status

### 2. Qdrant Search Issues

**Problem**: "No relevant documents found"
**Solution**:
- Verify documents are uploaded and processed
- Check Qdrant connection
- Verify embeddings are generated correctly

### 3. Streaming Issues

**Problem**: "Streaming connection terminated"
**Solution**:
- Check network connectivity
- Verify proxy settings
- Increase timeout values

### 4. Performance Issues

**Problem**: "Slow response times"
**Solution**:
- Optimize context search queries
- Implement result caching
- Consider using faster embedding models

## Test Data

### Sample Questions for Testing

1. **General Questions**:
   - "What documents do I have uploaded?"
   - "Can you summarize my documents?"
   - "What are the main topics covered?"

2. **Specific Content Questions**:
   - "Tell me about [specific topic from your documents]"
   - "Find information about [specific keyword]"
   - "Compare information across my documents"

3. **Complex Questions**:
   - "What are the key differences between document A and B?"
   - "Create a summary of all financial information"
   - "What action items are mentioned across all documents?"

### Sample Documents for Testing

Create test documents with:
- Known keywords and phrases
- Different topics and domains
- Various file formats
- Different lengths and complexity

## Deployment Testing

### 1. Production Environment

Before deploying to production:
- ✅ Run full test suite
- ✅ Verify environment variables
- ✅ Test with production data volume
- ✅ Verify SSL/HTTPS setup
- ✅ Test backup and recovery procedures

### 2. Staging Environment

- ✅ Deploy to staging first
- ✅ Run smoke tests
- ✅ Test with realistic data
- ✅ Perform load testing
- ✅ Verify monitoring and alerting

## Conclusion

This testing guide ensures the chat functionality is robust, secure, and performant. Regular testing should be performed especially when:

- Adding new document types
- Updating OpenAI models
- Changing context search algorithms
- Modifying streaming implementation
- Deploying to new environments

For automated testing, integrate these tests into your CI/CD pipeline to catch regressions early. 
