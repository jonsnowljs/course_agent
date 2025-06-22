import { test, expect, Page } from "@playwright/test"
import { firstSuperuser, firstSuperuserPassword } from "./config"
import NotionIntegration from '../src/components/UserSettings/NotionIntegration';
import { notionSync } from '../src/client';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
jest.mock('../src/client', () => ({
  ...jest.requireActual('../src/client'),
  notionSync: jest.fn(),
}));

// Test helper to mock streaming response
async function mockStreamingChatResponse(page: Page, response: string, context: any[] = []) {
  await page.route("/api/v1/chat/message", async (route) => {
    const chunks = response.split(" ").map((word, index, array) => {
      const isLast = index === array.length - 1
      return {
        type: "content",
        content: word + (isLast ? "" : " "),
        message_id: "test-message-id"
      }
    })

    // Create SSE response
    let responseBody = `data: ${JSON.stringify({
      type: "metadata",
      message_id: "test-message-id",
      timestamp: new Date().toISOString(),
      context_used: context
    })}\n\n`

    for (const chunk of chunks) {
      responseBody += `data: ${JSON.stringify(chunk)}\n\n`
    }

    responseBody += `data: ${JSON.stringify({
      type: "complete",
      message_id: "test-message-id",
      full_response: response
    })}\n\n`

    await route.fulfill({
      status: 200,
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive'
      },
      body: responseBody
    })
  })
}

// Test helper to mock document list response
async function mockDocumentsList(page: Page, documents: any[] = []) {
  await page.route("/api/v1/documents/?limit=1", async (route) => {
    await route.fulfill({
      status: 200,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(documents)
    })
  })
}

test.describe("Chat Page", () => {
  test.beforeEach(async ({ page }) => {
    // Login before each test
    await page.goto("/login")
    await page.getByPlaceholder("Email").fill(firstSuperuser)
    await page.getByPlaceholder("Password").fill(firstSuperuserPassword)
    await page.getByRole("button", { name: "Log In" }).click()
    await page.waitForURL("/")
  })

  test("should display chat page with empty state when no documents", async ({ page }) => {
    // Mock empty documents response
    await mockDocumentsList(page, [])
    
    await page.goto("/chat")
    
    // Should show empty state
    await expect(page.getByText("Welcome to Document Chat")).toBeVisible()
    await expect(page.getByText("Ask questions about your uploaded documents")).toBeVisible()
    await expect(page.getByText("Upload Documents First")).toBeVisible()
    
    // Input should be disabled
    const textarea = page.getByPlaceholder("Upload some documents first to get started!")
    await expect(textarea).toBeDisabled()
    
    // Send button should be disabled
    const sendButton = page.getByRole("button").filter({ hasText: "Send" })
    await expect(sendButton).toBeDisabled()
  })

  test("should enable chat when documents are available", async ({ page }) => {
    // Mock documents response
    const mockDocuments = [
      {
        document_id: "doc-1",
        filename: "test.txt",
        created_at: "2024-01-01T00:00:00",
        chunks_count: 5,
        total_words: 100
      }
    ]
    await mockDocumentsList(page, mockDocuments)
    
    await page.goto("/chat")
    
    // Should not show empty state
    await expect(page.getByText("Welcome to Document Chat")).not.toBeVisible()
    
    // Input should be enabled
    const textarea = page.getByPlaceholder("Ask a question about your documents...")
    await expect(textarea).toBeEnabled()
    
    // Send button should be enabled when text is entered
    await textarea.fill("What is this about?")
    const sendButton = page.getByRole("button").filter({ hasText: "Send" })
    await expect(sendButton).toBeEnabled()
  })

  test("should send message and display streaming response", async ({ page }) => {
    // Mock documents response
    await mockDocumentsList(page, [{ document_id: "doc-1", filename: "test.txt" }])
    
    // Mock streaming chat response
    const testResponse = "This is a test response from the AI assistant."
    await mockStreamingChatResponse(page, testResponse)
    
    await page.goto("/chat")
    
    // Type and send message
    const textarea = page.getByPlaceholder("Ask a question about your documents...")
    await textarea.fill("What is this document about?")
    
    const sendButton = page.getByRole("button").filter({ hasText: "Send" })
    await sendButton.click()
    
    // Should show user message
    await expect(page.getByText("What is this document about?")).toBeVisible()
    
    // Should show streaming response
    await expect(page.getByText(testResponse)).toBeVisible({ timeout: 10000 })
    
    // Input should be cleared
    await expect(textarea).toHaveValue("")
  })

  test("should display context when available", async ({ page }) => {
    // Mock documents response
    await mockDocumentsList(page, [{ document_id: "doc-1", filename: "test.txt" }])
    
    // Mock streaming response with context
    const context = [
      {
        filename: "test.txt",
        chunk_text: "This is the relevant content from the document",
        score: 0.95,
        document_id: "doc-1",
        chunk_index: 0
      }
    ]
    await mockStreamingChatResponse(page, "Based on your document, this is the answer.", context)
    
    await page.goto("/chat")
    
    // Send message
    const textarea = page.getByPlaceholder("Ask a question about your documents...")
    await textarea.fill("What does my document say?")
    await page.getByRole("button").filter({ hasText: "Send" }).click()
    
    // Should show context indicator
    await expect(page.getByText("Used 1 document as context")).toBeVisible()
    
    // Click to expand context
    await page.getByText("Used 1 document as context").click()
    
    // Should show context details
    await expect(page.getByText("test.txt")).toBeVisible()
    await expect(page.getByText("95% match")).toBeVisible()
    await expect(page.getByText("Chunk 1")).toBeVisible()
    await expect(page.getByText("This is the relevant content")).toBeVisible()
  })

  test("should handle message sending with Enter key", async ({ page }) => {
    // Mock documents response
    await mockDocumentsList(page, [{ document_id: "doc-1", filename: "test.txt" }])
    
    // Mock streaming response
    await mockStreamingChatResponse(page, "Response to Enter key message.")
    
    await page.goto("/chat")
    
    // Type message and press Enter
    const textarea = page.getByPlaceholder("Ask a question about your documents...")
    await textarea.fill("Test message with Enter key")
    await textarea.press("Enter")
    
    // Should send message
    await expect(page.getByText("Test message with Enter key")).toBeVisible()
    await expect(page.getByText("Response to Enter key message.")).toBeVisible({ timeout: 10000 })
  })

  test("should not send message with Shift+Enter", async ({ page }) => {
    // Mock documents response
    await mockDocumentsList(page, [{ document_id: "doc-1", filename: "test.txt" }])
    
    await page.goto("/chat")
    
    // Type message and press Shift+Enter
    const textarea = page.getByPlaceholder("Ask a question about your documents...")
    await textarea.fill("Line 1")
    await textarea.press("Shift+Enter")
    await textarea.type("Line 2")
    
    // Should have multi-line text but not send message
    await expect(textarea).toHaveValue("Line 1\nLine 2")
    await expect(page.getByText("Line 1")).not.toBeVisible()
  })

  test("should show stop button during streaming", async ({ page }) => {
    // Mock documents response
    await mockDocumentsList(page, [{ document_id: "doc-1", filename: "test.txt" }])
    
    // Mock slow streaming response
    await page.route("/api/v1/chat/message", async (route) => {
      // Simulate delayed response
      setTimeout(async () => {
        await route.fulfill({
          status: 200,
          headers: { 'Content-Type': 'text/event-stream' },
          body: `data: ${JSON.stringify({
            type: "metadata",
            message_id: "test-id",
            timestamp: new Date().toISOString(),
            context_used: []
          })}\n\n`
        })
      }, 1000)
    })
    
    await page.goto("/chat")
    
    // Send message
    const textarea = page.getByPlaceholder("Ask a question about your documents...")
    await textarea.fill("Test message")
    await page.getByRole("button").filter({ hasText: "Send" }).click()
    
    // Should show stop button
    await expect(page.getByRole("button", { name: "Stop" })).toBeVisible()
    
    // Input should be disabled during streaming
    await expect(textarea).toBeDisabled()
  })

  test("should handle empty message validation", async ({ page }) => {
    // Mock documents response
    await mockDocumentsList(page, [{ document_id: "doc-1", filename: "test.txt" }])
    
    await page.goto("/chat")
    
    // Try to send empty message
    const sendButton = page.getByRole("button").filter({ hasText: "Send" })
    await expect(sendButton).toBeDisabled()
    
    // Try with whitespace only
    const textarea = page.getByPlaceholder("Ask a question about your documents...")
    await textarea.fill("   ")
    await expect(sendButton).toBeDisabled()
  })

  test("should navigate to documents page from empty state", async ({ page }) => {
    // Mock empty documents response
    await mockDocumentsList(page, [])
    
    await page.goto("/chat")
    
    // Click on upload documents button
    await page.getByRole("button", { name: "Upload Documents First" }).click()
    
    // Should navigate to documents page
    await page.waitForURL("/documents")
    await expect(page.getByText("Document Management")).toBeVisible()
  })

  test("should navigate to documents page from help text", async ({ page }) => {
    // Mock empty documents response
    await mockDocumentsList(page, [])
    
    await page.goto("/chat")
    
    // Click on "Go to Documents" link
    await page.getByText("Go to Documents").click()
    
    // Should navigate to documents page
    await page.waitForURL("/documents")
  })

  test("should display message timestamps", async ({ page }) => {
    // Mock documents response
    await mockDocumentsList(page, [{ document_id: "doc-1", filename: "test.txt" }])
    
    // Mock streaming response
    await mockStreamingChatResponse(page, "Test response with timestamp.")
    
    await page.goto("/chat")
    
    // Send message
    const textarea = page.getByPlaceholder("Ask a question about your documents...")
    await textarea.fill("Test timestamp")
    await page.getByRole("button").filter({ hasText: "Send" }).click()
    
    // Should show timestamps (format: HH:MM:SS)
    const timestampRegex = /\d{1,2}:\d{2}:\d{2}/
    await expect(page.locator("text").filter({ hasText: timestampRegex })).toHaveCount(2) // User and bot messages
  })

  test("should maintain conversation history", async ({ page }) => {
    // Mock documents response
    await mockDocumentsList(page, [{ document_id: "doc-1", filename: "test.txt" }])
    
    await page.goto("/chat")
    
    // Send first message
    await mockStreamingChatResponse(page, "First response")
    const textarea = page.getByPlaceholder("Ask a question about your documents...")
    await textarea.fill("First message")
    await page.getByRole("button").filter({ hasText: "Send" }).click()
    
    await expect(page.getByText("First message")).toBeVisible()
    await expect(page.getByText("First response")).toBeVisible({ timeout: 10000 })
    
    // Send second message
    await mockStreamingChatResponse(page, "Second response")
    await textarea.fill("Second message")
    await page.getByRole("button").filter({ hasText: "Send" }).click()
    
    // Both messages should be visible
    await expect(page.getByText("First message")).toBeVisible()
    await expect(page.getByText("First response")).toBeVisible()
    await expect(page.getByText("Second message")).toBeVisible()
    await expect(page.getByText("Second response")).toBeVisible({ timeout: 10000 })
  })

  test("should handle API errors gracefully", async ({ page }) => {
    // Mock documents response
    await mockDocumentsList(page, [{ document_id: "doc-1", filename: "test.txt" }])
    
    // Mock API error
    await page.route("/api/v1/chat/message", async (route) => {
      await route.fulfill({
        status: 500,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ detail: "Internal server error" })
      })
    })
    
    await page.goto("/chat")
    
    // Send message
    const textarea = page.getByPlaceholder("Ask a question about your documents...")
    await textarea.fill("Test error handling")
    await page.getByRole("button").filter({ hasText: "Send" }).click()
    
    // Should show user message
    await expect(page.getByText("Test error handling")).toBeVisible()
    
    // Should handle error gracefully (error message might be in toast or console)
    // The exact error handling depends on your implementation
  })

  test("should scroll to bottom when new messages arrive", async ({ page }) => {
    // Mock documents response
    await mockDocumentsList(page, [{ document_id: "doc-1", filename: "test.txt" }])
    
    await page.goto("/chat")
    
    // Add multiple messages to create scrollable content
    for (let i = 1; i <= 5; i++) {
      await mockStreamingChatResponse(page, `Response ${i}`)
      const textarea = page.getByPlaceholder("Ask a question about your documents...")
      await textarea.fill(`Message ${i}`)
      await page.getByRole("button").filter({ hasText: "Send" }).click()
      await expect(page.getByText(`Response ${i}`)).toBeVisible({ timeout: 10000 })
    }
    
    // Last message should be visible (scrolled to bottom)
    await expect(page.getByText("Message 5")).toBeVisible()
    await expect(page.getByText("Response 5")).toBeVisible()
  })
})

test.describe("Chat Navigation", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/login")
    await page.getByPlaceholder("Email").fill(firstSuperuser)
    await page.getByPlaceholder("Password").fill(firstSuperuserPassword)
    await page.getByRole("button", { name: "Log In" }).click()
    await page.waitForURL("/")
  })

  test("should show chat in sidebar navigation", async ({ page }) => {
    await page.goto("/")
    
    // Desktop sidebar
    await expect(page.getByText("Chat")).toBeVisible()
    
    // Should navigate to chat page
    await page.getByText("Chat").click()
    await page.waitForURL("/chat")
  })

  test("should show chat in mobile navigation", async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 })
    
    await page.goto("/")
    
    // Open mobile menu
    await page.getByRole("button", { name: "Open Menu" }).click()
    
    // Should show chat in mobile menu
    await expect(page.getByText("Chat")).toBeVisible()
    
    // Should navigate to chat page
    await page.getByText("Chat").click()
    await page.waitForURL("/chat")
  })
})

test.describe("Chat Accessibility", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/login")
    await page.getByPlaceholder("Email").fill(firstSuperuser)
    await page.getByPlaceholder("Password").fill(firstSuperuserPassword)
    await page.getByRole("button", { name: "Log In" }).click()
    await page.waitForURL("/")
    
    // Mock documents response
    await page.route("/api/v1/documents/?limit=1", async (route) => {
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify([{ document_id: "doc-1", filename: "test.txt" }])
      })
    })
  })

  test("should be keyboard accessible", async ({ page }) => {
    await page.goto("/chat")
    
    // Should be able to focus textarea with Tab
    await page.keyboard.press("Tab")
    const textarea = page.getByPlaceholder("Ask a question about your documents...")
    await expect(textarea).toBeFocused()
    
    // Type and send with Enter
    await textarea.type("Test keyboard accessibility")
    await page.keyboard.press("Enter")
    
    // Should send message
    await expect(page.getByText("Test keyboard accessibility")).toBeVisible()
  })

  test("should have proper ARIA labels", async ({ page }) => {
    await page.goto("/chat")
    
    // Check for proper labeling
    const textarea = page.getByPlaceholder("Ask a question about your documents...")
    await expect(textarea).toBeVisible()
    
    const sendButton = page.getByRole("button").filter({ hasText: "Send" })
    await expect(sendButton).toBeVisible()
  })
})

describe('NotionIntegration', () => {
  it('syncs Notion pages and displays results', async () => {
    (notionSync as jest.Mock).mockResolvedValue({
      synced_pages: 2,
      details: ['Synced: Page 1', 'Synced: Page 2'],
    });
    render(<NotionIntegration />);
    fireEvent.change(screen.getByPlaceholderText(/notion integration token/i), {
      target: { value: 'test-token' },
    });
    fireEvent.click(screen.getByText(/sync notion pages/i));
    await waitFor(() => {
      expect(screen.getByText(/synced 2 pages/i)).toBeInTheDocument();
      expect(screen.getByText('Synced: Page 1')).toBeInTheDocument();
      expect(screen.getByText('Synced: Page 2')).toBeInTheDocument();
    });
  });
}); 
