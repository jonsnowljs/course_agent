import { useMutation, useQueryClient } from "@tanstack/react-query"
import React, { useRef, useState } from "react"

import {
  Button,
  DialogActionTrigger,
  DialogTitle,
  Text,
  VStack,
  Box,
  HStack,
  Progress,
  List,
} from "@chakra-ui/react"
import { FiUpload, FiFile, FiX, FiCheck } from "react-icons/fi"

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

interface FileWithProgress {
  file: File
  progress: number
  status: "pending" | "uploading" | "success" | "error"
  error?: string
}

const AddDocument = () => {
  const [isOpen, setIsOpen] = useState(false)
  const [files, setFiles] = useState<FileWithProgress[]>([])
  const [isDragOver, setIsDragOver] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const allowedTypes = [
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "text/markdown",
    "text/x-python",
    "text/javascript",
    "text/typescript",
    "application/javascript",
    "application/typescript",
  ]

  const mutation = useMutation({
    mutationFn: async (fileData: { file: File; index: number }) => {
      const formData = new FormData()
      formData.append("file", fileData.file)
      
      // Update file status to uploading
      setFiles(prev => prev.map((f, i) => 
        i === fileData.index 
          ? { ...f, status: "uploading" as const, progress: 10 }
          : f
      ))

      try {
        const response = await DocumentsService.uploadDocument({
          formData: { file: fileData.file }
        })
        
        // Success
        setFiles(prev => prev.map((f, i) => 
          i === fileData.index 
            ? { ...f, status: "success" as const, progress: 100 }
            : f
        ))
        
        return response
      } catch (error) {
        // Error
        setFiles(prev => prev.map((f, i) => 
          i === fileData.index 
            ? { 
                ...f, 
                status: "error" as const, 
                progress: 0,
                error: error instanceof Error ? error.message : "Upload failed"
              }
            : f
        ))
        throw error
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] })
      queryClient.invalidateQueries({ queryKey: ["documentStats"] })
    },
    onError: (err: ApiError) => {
      handleError(err)
    },
  })

  const handleFileSelect = (selectedFiles: FileList | null) => {
    if (!selectedFiles) return

    const newFiles: FileWithProgress[] = Array.from(selectedFiles)
      .filter(file => {
        // Check file type
        if (!allowedTypes.includes(file.type) && !file.name.match(/\.(md|py|js|ts|txt)$/i)) {
          showErrorToast(`File type not supported: ${file.name}`)
          return false
        }
        
        // Check file size (10MB limit)
        if (file.size > 10 * 1024 * 1024) {
          showErrorToast(`File too large: ${file.name} (max 10MB)`)
          return false
        }
        
        return true
      })
      .map(file => ({
        file,
        progress: 0,
        status: "pending" as const
      }))

    setFiles(prev => [...prev, ...newFiles])
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)
    handleFileSelect(e.dataTransfer.files)
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(true)
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)
  }

  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index))
  }

  const uploadFiles = async () => {
    const pendingFiles = files
      .map((fileWithProgress, index) => ({ ...fileWithProgress, index }))
      .filter(f => f.status === "pending")

    for (const fileData of pendingFiles) {
      try {
        await mutation.mutateAsync({
          file: fileData.file,
          index: fileData.index
        })
      } catch (error) {
        // Error handling is done in mutation
      }
    }

    // Check if all files were successful
    const allSuccessful = files.every(f => f.status === "success")
    if (allSuccessful && files.length > 0) {
      showSuccessToast(`${files.length} document(s) uploaded successfully`)
      setTimeout(() => {
        setFiles([])
        setIsOpen(false)
      }, 1500)
    }
  }

  const canUpload = files.some(f => f.status === "pending")
  const isUploading = files.some(f => f.status === "uploading")

  return (
    <DialogRoot
      size={{ base: "md", md: "lg" }}
      placement="center"
      open={isOpen}
      onOpenChange={({ open }) => {
        setIsOpen(open)
        if (!open) {
          setFiles([])
        }
      }}
    >
      <DialogTrigger asChild>
        <Button colorPalette="blue" my={4}>
          <FiUpload fontSize="16px" />
          Upload Documents
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Upload Documents</DialogTitle>
        </DialogHeader>
        <DialogBody>
          <VStack gap={4} align="stretch">
            <Text fontSize="sm" color="gray.600">
              Upload PDF, DOCX, TXT, Markdown, or code files (max 10MB each)
            </Text>

            {/* Drop Zone */}
            <Box
              border="2px dashed"
              borderColor={isDragOver ? "blue.400" : "gray.300"}
              borderRadius="md"
              p={8}
              textAlign="center"
              bg={isDragOver ? "blue.50" : "gray.50"}
              cursor="pointer"
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onClick={() => fileInputRef.current?.click()}
              transition="all 0.2s"
            >
              <VStack gap={2}>
                <FiUpload size={24} color={isDragOver ? "blue" : "gray"} />
                <Text fontWeight="medium">
                  Drop files here or click to browse
                </Text>
                <Text fontSize="sm" color="gray.500">
                  PDF, DOCX, TXT, MD, PY, JS, TS
                </Text>
              </VStack>
            </Box>

            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".pdf,.docx,.txt,.md,.py,.js,.ts"
              style={{ display: "none" }}
              onChange={(e) => handleFileSelect(e.target.files)}
            />

            {/* File List */}
            {files.length > 0 && (
              <VStack gap={2} align="stretch">
                <Text fontWeight="medium">Selected Files:</Text>
                <List.Root variant="plain" gap={2}>
                  {files.map((fileWithProgress, index) => (
                    <List.Item key={index}>
                      <Box
                        p={3}
                        border="1px solid"
                        borderColor="gray.200"
                        borderRadius="md"
                        bg="white"
                      >
                        <HStack justify="space-between" mb={2}>
                          <HStack gap={2} flex={1}>
                            {fileWithProgress.status === "success" ? (
                              <FiCheck color="green" />
                            ) : fileWithProgress.status === "error" ? (
                              <FiX color="red" />
                            ) : (
                              <FiFile />
                            )}
                            <Text
                              fontSize="sm"
                              fontWeight="medium"
                              truncate
                              maxW="200px"
                            >
                              {fileWithProgress.file.name}
                            </Text>
                            <Text fontSize="xs" color="gray.500">
                              ({(fileWithProgress.file.size / 1024 / 1024).toFixed(1)} MB)
                            </Text>
                          </HStack>
                          {fileWithProgress.status !== "uploading" && (
                            <Button
                              size="xs"
                              variant="ghost"
                              onClick={() => removeFile(index)}
                            >
                              <FiX />
                            </Button>
                          )}
                        </HStack>
                        
                        {fileWithProgress.status === "uploading" && (
                          <Progress.Root
                            value={fileWithProgress.progress}
                            size="sm"
                            colorPalette="blue"
                          >
                            <Progress.Track>
                              <Progress.Range />
                            </Progress.Track>
                          </Progress.Root>
                        )}
                        
                        {fileWithProgress.status === "error" && (
                          <Text fontSize="xs" color="red.500">
                            {fileWithProgress.error}
                          </Text>
                        )}
                      </Box>
                    </List.Item>
                  ))}
                </List.Root>
              </VStack>
            )}
          </VStack>
        </DialogBody>

        <DialogFooter gap={2}>
          <DialogActionTrigger asChild>
            <Button
              variant="subtle"
              colorPalette="gray"
              disabled={isUploading}
            >
              Cancel
            </Button>
          </DialogActionTrigger>
          <Button
            colorPalette="blue"
            onClick={uploadFiles}
            disabled={!canUpload}
            loading={isUploading}
          >
            Upload {files.filter(f => f.status === "pending").length} File(s)
          </Button>
        </DialogFooter>
        <DialogCloseTrigger />
      </DialogContent>
    </DialogRoot>
  )
}

export default AddDocument 
