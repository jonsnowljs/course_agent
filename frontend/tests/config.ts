import path from "node:path"
import { fileURLToPath } from "node:url"
import dotenv from "dotenv"

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

dotenv.config({ path: path.join(__dirname, "../../.env") })

const { FIRST_SUPERUSER, FIRST_SUPERUSER_PASSWORD } = process.env

if (typeof FIRST_SUPERUSER !== "string") {
  throw new Error("Environment variable FIRST_SUPERUSER is undefined")
}

if (typeof FIRST_SUPERUSER_PASSWORD !== "string") {
  throw new Error("Environment variable FIRST_SUPERUSER_PASSWORD is undefined")
}

export const firstSuperuser = FIRST_SUPERUSER as string
export const firstSuperuserPassword = FIRST_SUPERUSER_PASSWORD as string

export const testBaseURL = process.env.TEST_BASE_URL || "http://localhost:5173"
export const apiBaseURL = process.env.API_BASE_URL || "http://localhost:8000"

// Test data
export const testUser = {
  email: "test@example.com",
  password: "testpassword123",
  fullName: "Test User"
}

// Test documents
export const sampleDocuments = [
  {
    document_id: "test-doc-1",
    filename: "sample_document.txt",
    created_at: "2024-01-01T00:00:00",
    chunks_count: 5,
    total_words: 150
  },
  {
    document_id: "test-doc-2", 
    filename: "technical_guide.pdf",
    created_at: "2024-01-02T00:00:00",
    chunks_count: 10,
    total_words: 300
  }
]

// Sample chat responses for mocking
export const sampleChatResponses = {
  simple: "This is a simple test response from the AI assistant.",
  withContext: "Based on your document sample_document.txt, I can help you with that question.",
  error: "I apologize, but I encountered an error processing your request."
}

// Sample document context for chat
export const sampleContext = [
  {
    filename: "sample_document.txt",
    chunk_text: "This document contains information about machine learning algorithms and their applications in data science.",
    score: 0.95,
    document_id: "test-doc-1",
    chunk_index: 0,
    created_at: "2024-01-01T00:00:00"
  },
  {
    filename: "technical_guide.pdf", 
    chunk_text: "Python is widely used for implementing machine learning models due to its extensive ecosystem of libraries.",
    score: 0.87,
    document_id: "test-doc-2",
    chunk_index: 3,
    created_at: "2024-01-02T00:00:00"
  }
]
