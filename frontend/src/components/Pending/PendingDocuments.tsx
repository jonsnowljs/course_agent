import { Skeleton, Table, VStack } from "@chakra-ui/react"

const PendingDocuments = () => {
  return (
    <VStack gap={4} align="stretch">
      <Skeleton height="40px" />
      
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
          {Array.from({ length: 5 }).map((_, index) => (
            <Table.Row key={index}>
              <Table.Cell>
                <Skeleton height="20px" width="60%" />
              </Table.Cell>
              <Table.Cell>
                <Skeleton height="20px" width="40%" />
              </Table.Cell>
              <Table.Cell>
                <Skeleton height="20px" width="30%" />
              </Table.Cell>
              <Table.Cell>
                <Skeleton height="20px" width="35%" />
              </Table.Cell>
              <Table.Cell>
                <Skeleton height="20px" width="20px" />
              </Table.Cell>
            </Table.Row>
          ))}
        </Table.Body>
      </Table.Root>
    </VStack>
  )
}

export default PendingDocuments 
