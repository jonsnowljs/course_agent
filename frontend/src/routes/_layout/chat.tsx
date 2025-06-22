import { useState, useRef, useEffect } from "react"
import {
  Container,
  VStack,
  HStack,
  Box,
  Text,
  Input,
  Button,
  Flex,
  Badge,
  Textarea,
  IconButton,
  Spinner,
  Card,
  Heading,
  List,
  Collapsible,
  Separator
} from "@chakra-ui/react"
import { createFileRoute, Link } from "@tanstack/react-router"
import { FiSend, FiFile, FiChevronDown, FiChevronUp, FiMessageCircle, FiUpload } from "react-icons/fi"
import { useQuery } from "@tanstack/react-query"

import useCustomToast from "@/hooks/useCustomToast"
import { DocumentsService } from "@/client"

export const Route = createFileRoute("/_layout/chat")({
  component: ChatPage,
})

interface ChatMessage {
  id: string
  content: string
  isUser: boolean
  timestamp: string
  context?: ContextItem[]
}

interface ContextItem {
  filename: string
  chunk_text: string
  score: number
  document_id: string
  chunk_index: number
}

function ContextDisplay({ context }: { context: ContextItem[] }) {
  const [isOpen, setIsOpen] = useState(false)

  if (!context || context.length === 0) {
    return null
  }

  return (
    <Box mb={3}>
      <Collapsible.Root open={isOpen} onOpenChange={({ open }) => setIsOpen(open)}>
        <Collapsible.Trigger asChild>
          <Button 
            variant="ghost" 
            size="sm" 
            colorPalette="blue"
          >
            <FiFile />
            Used {context.length} document{context.length !== 1 ? 's' : ''} as context
            {isOpen ? <FiChevronUp /> : <FiChevronDown />}
          </Button>
        </Collapsible.Trigger>
        <Collapsible.Content>
          <VStack gap={2} mt={2} align="stretch">
            {context.map((item, index) => (
              <Card.Root key={`${item.document_id}-${item.chunk_index}`} size="sm" variant="outline">
                <Card.Body p={3}>
                  <HStack justify="space-between" mb={2}>
                    <HStack gap={2}>
                      <FiFile size="14" />
                      <Text fontSize="sm" fontWeight="medium">
                        {item.filename}
                      </Text>
                    </HStack>
                    <HStack gap={2}>
                      <Badge colorPalette="green" variant="surface" fontSize="xs">
                        {Math.round(item.score * 100)}% match
                      </Badge>
                      <Badge colorPalette="blue" variant="surface" fontSize="xs">
                        Chunk {item.chunk_index + 1}
                      </Badge>
                    </HStack>
                  </HStack>
                  <Text fontSize="sm" color="gray.600" lineClamp={3}>
                    {item.chunk_text}
                  </Text>
                </Card.Body>
              </Card.Root>
            ))}
          </VStack>
        </Collapsible.Content>
      </Collapsible.Root>
    </Box>
  )
}

function MessageBubble({ message }: { message: ChatMessage }) {
  return (
    <Flex justify={message.isUser ? "flex-end" : "flex-start"} w="full">
      <Box
        maxW="80%"
        bg={message.isUser ? "blue.500" : "gray.100"}
        color={message.isUser ? "white" : "gray.800"}
        px={4}
        py={3}
        borderRadius="lg"
        borderBottomRightRadius={message.isUser ? "md" : "lg"}
        borderBottomLeftRadius={message.isUser ? "lg" : "md"}
      >
        {!message.isUser && message.context && (
          <ContextDisplay context={message.context} />
        )}
        <Text fontSize="sm" whiteSpace="pre-wrap" lineHeight="1.5">
          {message.content}
        </Text>
        <Text fontSize="xs" opacity={0.7} mt={2}>
          {new Date(message.timestamp).toLocaleTimeString()}
        </Text>
      </Box>
    </Flex>
  )
}

function EmptyChat() {
  return (
    <VStack gap={4} justify="center" flex={1} py={20}>
      <FiMessageCircle size={48} color="gray" />
      <VStack gap={2} textAlign="center">
        <Heading size="lg" color="gray.600">
          Welcome to Document Chat
        </Heading>
        <Text color="gray.500" maxW="md">
          Ask questions about your uploaded documents and get AI-powered answers with context.
        </Text>
      </VStack>
      <Button colorPalette="blue" variant="outline" asChild>
        <Link to="/documents">
          <FiUpload />
          Upload Documents First
        </Link>
      </Button>
    </VStack>
  )
}

function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [streamingMessage, setStreamingMessage] = useState("")
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const abortControllerRef = useRef<AbortController | null>(null)
  const { showErrorToast } = useCustomToast()

  // Check if user has documents
  const { data: documents } = useQuery({
    queryKey: ["documents"],
    queryFn: () => DocumentsService.listUserDocuments({ limit: 1 }),
  })

  const hasDocuments = documents && documents.length > 0

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, streamingMessage])

  const sendMessage = async () => {
    if (!input.trim() || isLoading) return

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      content: input.trim(),
      isUser: true,
      timestamp: new Date().toISOString(),
    }

    setMessages(prev => [...prev, userMessage])
    setInput("")
    setIsLoading(true)
    setStreamingMessage("")

    // Create abort controller for this request
    abortControllerRef.current = new AbortController()

    try {
      const response = await fetch("/api/v1/chat/message", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${localStorage.getItem("access_token")}`,
        },
        body: JSON.stringify({
          message: input.trim(),
          context_limit: 5,
          stream: true,
        }),
        signal: abortControllerRef.current.signal,
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const reader = response.body?.getReader()
      if (!reader) {
        throw new Error("No response body")
      }

      let botMessage: ChatMessage = {
        id: "",
        content: "",
        isUser: false,
        timestamp: new Date().toISOString(),
        context: [],
      }

      const decoder = new TextDecoder()
      let buffer = ""

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split("\n\n")
        buffer = lines.pop() || "" // Keep incomplete line in buffer

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const data = JSON.parse(line.slice(6))
              
              if (data.type === "metadata") {
                botMessage.id = data.message_id
                botMessage.timestamp = data.timestamp
                botMessage.context = data.context_used
              } else if (data.type === "content") {
                botMessage.content += data.content
                setStreamingMessage(botMessage.content)
              } else if (data.type === "complete") {
                botMessage.content = data.full_response
                setMessages(prev => [...prev, botMessage])
                setStreamingMessage("")
              } else if (data.type === "error") {
                throw new Error(data.error)
              }
            } catch (error) {
              console.error("Error parsing SSE data:", error)
            }
          }
        }
      }
    } catch (error: any) {
      if (error.name === "AbortError") {
        console.log("Request aborted")
      } else {
        console.error("Chat error:", error)
        showErrorToast(`Failed to send message: ${error.message}`)
      }
      setStreamingMessage("")
    } finally {
      setIsLoading(false)
      abortControllerRef.current = null
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const stopGeneration = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }
  }

  return (
    <Container maxW="4xl" h="100vh" py={4}>
      <VStack gap={4} h="full">
        {/* Header */}
        <Box w="full" borderBottom="1px" borderColor="gray.200" pb={4}>
          <Heading size="lg" mb={2}>
            Document Chat
          </Heading>
          <Text color="gray.600" fontSize="sm">
            Chat with your uploaded documents using AI
          </Text>
        </Box>

        {/* Messages Area */}
        <VStack
          gap={4}
          flex={1}
          w="full"
          overflowY="auto"
          p={4}
          bg="gray.50"
          borderRadius="lg"
        >
          {messages.length === 0 && !hasDocuments ? (
            <EmptyChat />
          ) : (
            <>
              {messages.map((message) => (
                <MessageBubble key={message.id} message={message} />
              ))}
              
              {/* Streaming message */}
              {streamingMessage && (
                <Flex justify="flex-start" w="full">
                  <Box
                    maxW="80%"
                    bg="gray.100"
                    color="gray.800"
                    px={4}
                    py={3}
                    borderRadius="lg"
                    borderBottomLeftRadius="md"
                  >
                    <Text fontSize="sm" whiteSpace="pre-wrap" lineHeight="1.5">
                      {streamingMessage}
                      <Box as="span" display="inline-block" w="2px" h="1em" bg="gray.600" ml={1} />
                    </Text>
                  </Box>
                </Flex>
              )}
            </>
          )}
          <div ref={messagesEndRef} />
        </VStack>

        {/* Input Area */}
        <Box w="full">
          <HStack gap={2}>
            <Textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder={
                hasDocuments 
                  ? "Ask a question about your documents..." 
                  : "Upload some documents first to get started!"
              }
              resize="none"
              rows={2}
              disabled={isLoading || !hasDocuments}
            />
            {isLoading ? (
              <Button
                colorPalette="red"
                variant="outline"
                onClick={stopGeneration}
                px={6}
              >
                Stop
              </Button>
            ) : (
              <Button
                colorPalette="blue"
                onClick={sendMessage}
                disabled={!input.trim() || !hasDocuments}
                px={6}
              >
                <FiSend />
              </Button>
            )}
          </HStack>
          
          {!hasDocuments && (
            <Text fontSize="xs" color="gray.500" mt={2} textAlign="center">
              You need to upload documents first before you can chat. 
              <Link to="/documents">
                <Text as="span" color="blue.500" cursor="pointer" textDecoration="underline">
                  Go to Documents
                </Text>
              </Link>
            </Text>
          )}
        </Box>
      </VStack>
    </Container>
  )
} 
