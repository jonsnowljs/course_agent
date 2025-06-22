# Documents UI Feature

This document describes the newly implemented Documents UI feature that provides document upload, management, and semantic search capabilities.

## Overview

The Documents UI allows users to:
- Upload multiple document types (PDF, DOCX, TXT, MD, Python, JavaScript, TypeScript)
- View uploaded documents with metadata (chunks, word count, upload date)
- Search through documents using semantic similarity
- Delete unwanted documents
- View document statistics

## Components

### 1. Documents Route (`/documents`)
- **Location**: `frontend/src/routes/_layout/documents.tsx`
- **Features**:
  - Document statistics dashboard
  - Upload and search buttons
  - Documents table with filtering
  - Empty states for no documents

### 2. Upload Component
- **Location**: `frontend/src/components/Documents/AddDocument.tsx`
- **Features**:
  - Drag-and-drop file upload
  - Multiple file support
  - File type validation (PDF, DOCX, TXT, MD, PY, JS, TS)
  - File size validation (10MB limit)
  - Progress tracking for uploads
  - Error handling with toast notifications

### 3. Search Component
- **Location**: `frontend/src/components/Documents/DocumentSearch.tsx`
- **Features**:
  - Semantic search through uploaded documents
  - Real-time search results with relevance scores
  - Text highlighting for search terms
  - Chunk information display
  - Search result pagination

### 4. Delete Component
- **Location**: `frontend/src/components/Documents/DeleteDocument.tsx`
- **Features**:
  - Confirmation dialog for document deletion
  - Safe deletion with user confirmation
  - Toast notifications for successful deletion

## Navigation

The Documents feature is accessible from the sidebar navigation with a file icon (📄) labeled "Documents".

## API Integration

The UI integrates with the following backend endpoints:

### Document Endpoints
- `POST /api/v1/documents/upload/` - Upload documents
- `GET /api/v1/documents/` - List user documents
- `POST /api/v1/documents/search/` - Search documents
- `DELETE /api/v1/documents/{document_id}` - Delete document
- `GET /api/v1/documents/stats/` - Get document statistics

### Backend Features
- **Text Extraction**: Supports PDF, DOCX, TXT, MD, and code files
- **Text Chunking**: Intelligent text splitting with overlap
- **OpenAI Embeddings**: Uses OpenAI API for semantic embeddings
- **Qdrant Storage**: Vector database for similarity search
- **User Isolation**: Documents are isolated per user

## Usage

### Uploading Documents

1. Click "Upload Documents" button
2. Drag files onto the drop zone or click to browse
3. Select multiple files (up to 10MB each)
4. Click "Upload X File(s)" to process
5. Monitor upload progress for each file
6. View success/error status for each upload

### Searching Documents

1. Click "Search Documents" button
2. Enter your search query (e.g., "What is machine learning?")
3. Press Enter or click search button
4. View results with relevance scores and highlighted text
5. See which document chunk contains the matching content

### Managing Documents

1. View all uploaded documents in the table
2. Filter documents by filename using the search input
3. See document metadata: upload date, chunk count, word count
4. Delete documents using the trash icon with confirmation

## File Format Support

- **PDF**: Extracts text content using PyPDF2
- **DOCX**: Extracts text from Word documents using python-docx
- **TXT**: Plain text files with encoding detection
- **Markdown**: .md files treated as text
- **Code Files**: Python (.py), JavaScript (.js), TypeScript (.ts)

## Technical Implementation

### Frontend Stack
- **React 18** with TypeScript
- **Chakra UI v3** for components
- **React Query** for API state management
- **React Router** for navigation
- **React Hook Form** for form handling

### State Management
- React Query for server state
- Local component state for UI interactions
- Toast notifications for user feedback

### Error Handling
- Comprehensive error boundaries
- API error handling with user-friendly messages
- File validation with clear error messages
- Loading states and progress indicators

### Performance
- Lazy loading of components
- Efficient re-renders with React Query
- Optimistic updates where appropriate
- Debounced search to avoid excessive API calls

## Environment Setup

### Backend Requirements
```bash
# Required environment variables
OPENAI_API_KEY=your_openai_api_key
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=your_qdrant_api_key (optional)
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

### Backend Setup
```bash
cd backend
pip install -e .
uvicorn app.main:app --reload
```

## Development

### Adding New File Types
1. Update `allowedTypes` array in `AddDocument.tsx`
2. Add file extension to accept attribute
3. Implement text extraction in backend `embeddings.py`
4. Test upload and search functionality

### Customizing Search
- Modify search limit in `DocumentSearch.tsx`
- Adjust chunk size in backend configuration
- Customize relevance score thresholds
- Add search filters (date, file type, etc.)

### UI Customization
- Modify Chakra UI theme tokens
- Customize component variants
- Add new color schemes
- Enhance responsive design

## Testing

The components include comprehensive error handling and loading states. Test scenarios include:
- File upload validation
- Network error handling
- Search with no results
- Large file handling
- Multiple simultaneous uploads

## Future Enhancements

Potential improvements for the Documents UI:
- File preview functionality
- Batch operations (select multiple documents)
- Advanced search filters
- Document tagging and categorization
- Export search results
- Document sharing between users
- Version control for documents 
