import { useMutation } from "@tanstack/react-query"
import React, { useState } from "react"

import {
  Button,
  DialogActionTrigger,
  DialogTitle,
  Text,
  VStack,
  Input,
  HStack,
  Badge,
  Box,
  List,
  Spinner,
} from "@chakra-ui/react"
import { FiSearch, FiFileText } from "react-icons/fi"

import { DocumentsService } from "@/client"
import type { ApiError } from "@/client/core/ApiError"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"
import {
  DialogBody,
  DialogCloseTrigger,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogRoot,
  DialogTrigger,
} from "../ui/dialog"
import { Field } from "../ui/field"

import type { SearchResult } from "@/client"

const DocumentSearch = () => {
  const [isOpen, setIsOpen] = useState(false)
  const [query, setQuery] = useState("")
  const [results, setResults] = useState<SearchResult[]>([])
  const { showErrorToast } = useCustomToast()

  const mutation = useMutation({
    mutationFn: async (searchQuery: string) => {
      const response = await DocumentsService.searchUserDocuments({
        requestBody: {
          query: searchQuery,
          limit: 10
        }
      })
      return response
    },
    onSuccess: (data) => {
      setResults(data)
    },
    onError: (err: ApiError) => {
      handleError(err)
      showErrorToast("Failed to search documents")
    },
  })

  const handleSearch = () => {
    if (!query.trim()) {
      showErrorToast("Please enter a search query")
      return
    }
    mutation.mutate(query.trim())
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSearch()
    }
  }

  const highlightText = (text: string, query: string) => {
    if (!query) return text
    
    const regex = new RegExp(`(${query})`, 'gi')
    const parts = text.split(regex)
    
    return parts.map((part, index) => 
      regex.test(part) ? (
        <mark key={index} style={{ backgroundColor: '#yellow.200', fontWeight: 'bold' }}>
          {part}
        </mark>
      ) : part
    )
  }

  return (
    <DialogRoot
      size={{ base: "md", md: "xl" }}
      placement="center"
      open={isOpen}
      onOpenChange={({ open }) => {
        setIsOpen(open)
        if (!open) {
          setQuery("")
          setResults([])
        }
      }}
    >
      <DialogTrigger asChild>
        <Button variant="outline" colorPalette="gray">
          <FiSearch fontSize="16px" />
          Search Documents
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Search Documents</DialogTitle>
        </DialogHeader>
        <DialogBody>
          <VStack gap={4} align="stretch">
            <Text fontSize="sm" color="gray.600">
              Search through your uploaded documents using semantic similarity
            </Text>

            <Field label="Search Query">
              <HStack>
                <Input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="e.g., What is machine learning?"
                  size="md"
                  disabled={mutation.isPending}
                />
                <Button
                  onClick={handleSearch}
                  disabled={!query.trim() || mutation.isPending}
                  loading={mutation.isPending}
                  colorPalette="blue"
                >
                  <FiSearch />
                </Button>
              </HStack>
            </Field>

            {/* Results */}
            {mutation.isPending && (
              <Box textAlign="center" py={4}>
                <Spinner size="md" />
                <Text mt={2} fontSize="sm" color="gray.600">
                  Searching documents...
                </Text>
              </Box>
            )}

            {results.length > 0 && (
              <VStack gap={3} align="stretch">
                <Text fontWeight="medium">
                  Found {results.length} result{results.length !== 1 ? 's' : ''}
                </Text>
                                 <List.Root variant="plain" gap={3}>
                  {results.map((result) => (
                    <List.Item key={`${result.document_id}-${result.chunk_index}`}>
                      <Box
                        p={4}
                        border="1px solid"
                        borderColor="gray.200"
                        borderRadius="md"
                        bg="white"
                        _hover={{ borderColor: "blue.300" }}
                        transition="border-color 0.2s"
                      >
                        <HStack justify="space-between" mb={2}>
                          <HStack gap={2}>
                            <FiFileText color="blue" />
                            <Text fontWeight="medium" fontSize="sm">
                              {result.filename}
                            </Text>
                          </HStack>
                          <HStack gap={2}>
                            <Badge colorPalette="green" variant="surface" fontSize="xs">
                              {Math.round(result.score * 100)}% match
                            </Badge>
                            <Badge colorPalette="blue" variant="surface" fontSize="xs">
                              Chunk {result.chunk_index + 1}
                            </Badge>
                          </HStack>
                        </HStack>
                        
                        <Text
                          fontSize="sm"
                          color="gray.700"
                          lineHeight="1.5"
                          lineClamp={4}
                        >
                          {highlightText(result.chunk_text, query)}
                        </Text>
                      </Box>
                    </List.Item>
                  ))}
                </List.Root>
              </VStack>
            )}

            {!mutation.isPending && results.length === 0 && query && mutation.isSuccess && (
              <Box textAlign="center" py={8}>
                <FiSearch size={32} color="gray" />
                <Text mt={2} fontWeight="medium" color="gray.600">
                  No results found
                </Text>
                <Text fontSize="sm" color="gray.500">
                  Try using different keywords or check your spelling
                </Text>
              </Box>
            )}
          </VStack>
        </DialogBody>

        <DialogFooter>
          <DialogActionTrigger asChild>
            <Button variant="subtle" colorPalette="gray">
              Close
            </Button>
          </DialogActionTrigger>
        </DialogFooter>
        <DialogCloseTrigger />
      </DialogContent>
    </DialogRoot>
  )
}

export default DocumentSearch 
