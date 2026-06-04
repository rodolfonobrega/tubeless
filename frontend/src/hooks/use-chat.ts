import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { chatApi } from '@/lib/api'
import type { ChatMessage, ChatRequest, ChatSource } from '@/types'

interface UseChatOptions {
  enabled?: boolean
  onChunk?: (chunk: string) => void
  onSource?: (sources: ChatSource[]) => void
}

export function useChatMessages(projectId: string | null, options: UseChatOptions = {}) {
  const queryClient = useQueryClient()
  const { enabled = true, onChunk, onSource } = options

  const query = useQuery({
    queryKey: ['chat', projectId],
    queryFn: (): Promise<ChatMessage[]> => Promise.resolve([]),
    enabled: !!projectId && enabled,
    staleTime: 10_000,
  })

  const sendMessage = useMutation({
    mutationFn: async (params: { message: string; videoIds?: string[] }) => {
      const { message, videoIds } = params
      if (!projectId) throw new Error('No project ID')

      // Optimistically add user message
      const userMessage: ChatMessage = {
        id: `temp-${Date.now()}`,
        project_id: projectId,
        role: 'user',
        content: message,
        sources: [],
        created_at: new Date().toISOString(),
      }

      queryClient.setQueryData<ChatMessage[]>(['chat', projectId], (old = []) => [
        ...old,
        userMessage,
      ])

      // Add placeholder for assistant response
      const assistantMessage: ChatMessage = {
        id: `temp-assistant-${Date.now()}`,
        project_id: projectId,
        role: 'assistant',
        content: '',
        sources: [],
        created_at: new Date().toISOString(),
      }

      queryClient.setQueryData<ChatMessage[]>(['chat', projectId], (old = []) => [
        ...old,
        assistantMessage,
      ])

      // Stream the response
      await chatApi.streamMessage(
        { message, project_id: projectId, video_ids: videoIds },
        (chunk) => {
          // Update the assistant message with new content
          queryClient.setQueryData<ChatMessage[]>(['chat', projectId], (old = []) => {
            const messages = [...old]
            const lastMessage = messages[messages.length - 1]
            if (lastMessage?.role === 'assistant') {
              lastMessage.content += chunk
              onChunk?.(chunk)
            }
            return messages
          })
        },
        (sources) => {
          // Update sources when complete
          queryClient.setQueryData<ChatMessage[]>(['chat', projectId], (old = []) => {
            const messages = [...old]
            const lastMessage = messages[messages.length - 1]
            if (lastMessage?.role === 'assistant') {
              lastMessage.sources = sources
              onSource?.(sources)
            }
            return messages
          })
        },
        (error) => {
          // Remove the assistant message on error
          queryClient.setQueryData<ChatMessage[]>(['chat', projectId], (old = []) => {
            const messages = [...old]
            if (
              messages.length >= 2 &&
              messages[messages.length - 1].role === 'assistant'
            ) {
              messages.pop()
            }
            return messages
          })
          throw error
        }
      )

      // Invalidate to get fresh data from server
      queryClient.invalidateQueries({ queryKey: ['chat', projectId] })
    },
  })

  return {
    messages: query.data || [],
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    sendMessage: sendMessage.mutate,
    isSending: sendMessage.isPending,
    refetch: query.refetch,
  }
}

export function useChatStreaming() {
  const queryClient = useQueryClient()

  const sendMessage = async (params: ChatRequest): Promise<void> => {
    const { message, project_id } = params

    // Optimistically add user message
    const userMessage: ChatMessage = {
      id: `temp-${Date.now()}`,
      project_id,
      role: 'user',
      content: message,
      sources: [],
      created_at: new Date().toISOString(),
    }

    queryClient.setQueryData<ChatMessage[]>(['chat', project_id], (old = []) => [
      ...old,
      userMessage,
    ])

    // Stream response using the API
    return chatApi.streamMessage(
      params,
      (chunk) => {
        queryClient.setQueryData<ChatMessage[]>(['chat', project_id], (old = []) => {
          const messages = [...old]
          const lastMessage = messages[messages.length - 1]
          if (lastMessage?.role === 'assistant') {
            lastMessage.content += chunk
          }
          return messages
        })
      },
      (sources) => {
        queryClient.setQueryData<ChatMessage[]>(['chat', project_id], (old = []) => {
          const messages = [...old]
          const lastMessage = messages[messages.length - 1]
          if (lastMessage?.role === 'assistant') {
            lastMessage.sources = sources
          }
          return messages
        })
      },
      (error) => {
        queryClient.setQueryData<ChatMessage[]>(['chat', project_id], (old = []) => {
          const messages = [...old]
          if (messages.length >= 2 && messages[messages.length - 1].role === 'assistant') {
            messages.pop()
          }
          return messages
        })
        throw error
      }
    )
  }

  return { sendMessage }
}
