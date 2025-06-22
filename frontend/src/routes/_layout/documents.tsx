import {
  Container,
  EmptyState,
  Flex,
  Heading,
  HStack,
  Input,
  Table,
  VStack,
  Text,
  Badge,
} from "@chakra-ui/react"
import { useQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { useState } from "react"
import { FiFileText } from "react-icons/fi"

import { DocumentsService } from "@/client"
import AddDocument from "@/components/Documents/AddDocument"
import DocumentSearch from "@/components/Documents/DocumentSearch"
import DeleteDocument from "@/components/Documents/DeleteDocument"
import PendingDocuments from "@/components/Pending/PendingDocuments"
import { Field } from "@/components/ui/field"

export const Route = createFileRoute("/_layout/documents")({
  component: Documents,
})

function DocumentsTable() {
  const [searchTerm, setSearchTerm] = useState("")

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["documents"],
    queryFn: () => DocumentsService.listUserDocuments({ limit: 100 }),
  })

  const documents = data || []

  // Filter documents based on search term
  const filteredDocuments = documents.filter((doc) =>
    doc.filename.toLowerCase().includes(searchTerm.toLowerCase())
  )

  if (isLoading) {
    return <PendingDocuments />
  }

  if (documents.length === 0) {
    return (
      <EmptyState.Root>
        <EmptyState.Content>
          <EmptyState.Indicator>
            <FiFileText />
          </EmptyState.Indicator>
          <VStack textAlign="center">
            <EmptyState.Title>No documents uploaded yet</EmptyState.Title>
            <EmptyState.Description>
              Upload your first document to get started with semantic search
            </EmptyState.Description>
          </VStack>
        </EmptyState.Content>
      </EmptyState.Root>
    )
  }

  return (
    <VStack gap={4} align="stretch">
      <Field label="Filter Documents">
        <Input
          placeholder="Search by filename..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          size="md"
        />
      </Field>

      <Table.Root size={{ base: "sm", md: "md" }}>
        <Table.Header>
          <Table.Row>
            <Table.ColumnHeader>Filename</Table.ColumnHeader>
            <Table.ColumnHeader>Upload Date</Table.ColumnHeader>
            <Table.ColumnHeader>Chunks</Table.ColumnHeader>
            <Table.ColumnHeader>Words</Table.ColumnHeader>
            <Table.ColumnHeader>Actions</Table.ColumnHeader>
          </Table.Row>
        </Table.Header>
        <Table.Body>
          {filteredDocuments.map((document) => (
            <Table.Row key={document.document_id}>
              <Table.Cell>
                <HStack gap={2}>
                  <FiFileText />
                  <Text fontWeight="medium" truncate maxW="200px">
                    {document.filename}
                  </Text>
                </HStack>
              </Table.Cell>
              <Table.Cell>
                <Text fontSize="sm" color="gray.600">
                  {new Date(document.created_at).toLocaleDateString()}
                </Text>
              </Table.Cell>
              <Table.Cell>
                <Badge colorPalette="blue" variant="surface">
                  {document.chunks_count}
                </Badge>
              </Table.Cell>
              <Table.Cell>
                <Badge colorPalette="green" variant="surface">
                  {document.total_words.toLocaleString()}
                </Badge>
              </Table.Cell>
              <Table.Cell>
                <DeleteDocument
                  documentId={document.document_id}
                  filename={document.filename}
                  onSuccess={() => refetch()}
                />
              </Table.Cell>
            </Table.Row>
          ))}
        </Table.Body>
      </Table.Root>

      {filteredDocuments.length === 0 && searchTerm && (
        <Text textAlign="center" color="gray.500" py={4}>
          No documents found matching "{searchTerm}"
        </Text>
      )}
    </VStack>
  )
}

function DocumentStats() {
  const { data: stats } = useQuery({
    queryKey: ["documentStats"],
    queryFn: () => DocumentsService.getUserDocumentStats(),
  })

  if (!stats) return null

  // Type assertion since we know the structure from the backend
  const typedStats = stats as {
    total_documents: number
    total_chunks: number
    total_words: number
  }

  return (
    <HStack gap={6} p={4} bg="gray.50" borderRadius="md">
      <VStack gap={1} align="center">
        <Text fontSize="2xl" fontWeight="bold" color="blue.500">
          {typedStats.total_documents}
        </Text>
        <Text fontSize="sm" color="gray.600">
          Documents
        </Text>
      </VStack>
      <VStack gap={1} align="center">
        <Text fontSize="2xl" fontWeight="bold" color="green.500">
          {typedStats.total_chunks}
        </Text>
        <Text fontSize="sm" color="gray.600">
          Chunks
        </Text>
      </VStack>
      <VStack gap={1} align="center">
        <Text fontSize="2xl" fontWeight="bold" color="purple.500">
          {typedStats.total_words.toLocaleString()}
        </Text>
        <Text fontSize="sm" color="gray.600">
          Words
        </Text>
      </VStack>
    </HStack>
  )
}

function Documents() {
  return (
    <Container maxW="full">
      <Heading size="lg" pt={12} mb={6}>
        Document Management
      </Heading>
      
      <DocumentStats />
      
      <Flex gap={4} my={6} direction={{ base: "column", md: "row" }}>
        <AddDocument />
        <DocumentSearch />
      </Flex>

      <DocumentsTable />
    </Container>
  )
} 
