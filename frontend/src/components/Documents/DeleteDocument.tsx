import { useMutation } from "@tanstack/react-query"
import React, { useState } from "react"

import {
  Button,
  DialogActionTrigger,
  DialogTitle,
  Text,
  VStack,
} from "@chakra-ui/react"
import { FiTrash2 } from "react-icons/fi"

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

interface DeleteDocumentProps {
  documentId: string
  filename: string
  onSuccess?: () => void
}

const DeleteDocument: React.FC<DeleteDocumentProps> = ({
  documentId,
  filename,
  onSuccess
}) => {
  const [isOpen, setIsOpen] = useState(false)
  const { showSuccessToast } = useCustomToast()

  const mutation = useMutation({
    mutationFn: () => DocumentsService.deleteUserDocument({ 
      documentId: documentId 
    }),
    onSuccess: () => {
      showSuccessToast(`Document "${filename}" deleted successfully`)
      setIsOpen(false)
      onSuccess?.()
    },
    onError: (err: ApiError) => {
      handleError(err)
    },
  })

  const handleDelete = () => {
    mutation.mutate()
  }

  return (
    <DialogRoot
      size={{ base: "xs", md: "md" }}
      placement="center"
      open={isOpen}
      onOpenChange={({ open }) => setIsOpen(open)}
    >
      <DialogTrigger asChild>
        <Button 
          size="xs" 
          variant="ghost" 
          colorPalette="red"
          aria-label={`Delete ${filename}`}
        >
          <FiTrash2 />
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Delete Document</DialogTitle>
        </DialogHeader>
        <DialogBody>
          <VStack gap={4} align="stretch">
            <Text>
              Are you sure you want to delete this document? This action cannot be undone.
            </Text>
            <Text fontWeight="medium" color="red.600">
              "{filename}"
            </Text>
            <Text fontSize="sm" color="gray.600">
              This will permanently remove the document and all its associated chunks from your collection.
            </Text>
          </VStack>
        </DialogBody>

        <DialogFooter gap={2}>
          <DialogActionTrigger asChild>
            <Button
              variant="subtle"
              colorPalette="gray"
              disabled={mutation.isPending}
            >
              Cancel
            </Button>
          </DialogActionTrigger>
          <Button
            colorPalette="red"
            onClick={handleDelete}
            loading={mutation.isPending}
          >
            Delete Document
          </Button>
        </DialogFooter>
        <DialogCloseTrigger />
      </DialogContent>
    </DialogRoot>
  )
}

export default DeleteDocument 
