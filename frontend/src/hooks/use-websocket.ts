import { useEffect, useRef, useCallback } from 'react'
import type { WebSocketMessage, StatusUpdateMessage, ProgressMessage } from '@/types'

interface UseWebSocketOptions {
  onStatusUpdate?: (data: StatusUpdateMessage['data']) => void
  onProgress?: (data: ProgressMessage['data']) => void
  onComplete?: (projectId: string) => void
  onError?: (message: string) => void
  onConnect?: () => void
  onDisconnect?: () => void
}

const MAX_RECONNECTS = 2

export function useWebSocket(projectId: string | null, options: UseWebSocketOptions = {}) {
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const isManuallyClosedRef = useRef(false)
  const reconnectCountRef = useRef(0)

  const connect = useCallback(() => {
    if (!projectId) return
    if (reconnectCountRef.current >= MAX_RECONNECTS) return

    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsBase = process.env.NEXT_PUBLIC_WS_URL
      ? process.env.NEXT_PUBLIC_WS_URL
      : `${wsProtocol}//${window.location.host}`

    try {
      const ws = new WebSocket(`${wsBase}/ws/projects/${projectId}`)
      wsRef.current = ws

      ws.onopen = () => {
        // If disconnect() was called while we were connecting, close immediately
        if (isManuallyClosedRef.current) {
          ws.close(1000, 'Disconnected')
          return
        }
        reconnectCountRef.current = 0
        options.onConnect?.()
        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current)
          reconnectTimeoutRef.current = null
        }
      }

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data)
          switch (message.type) {
            case 'status_update':
              options.onStatusUpdate?.(message.data as StatusUpdateMessage['data'])
              break
            case 'progress':
              options.onProgress?.(message.data as ProgressMessage['data'])
              break
            case 'complete':
              options.onComplete?.(message.project_id)
              break
            case 'error':
              options.onError?.((message.data as { message: string }).message)
              break
          }
        } catch {
          // ignore parse errors
        }
      }

      ws.onclose = (event) => {
        options.onDisconnect?.()
        if (
          !isManuallyClosedRef.current &&
          event.code !== 1000 &&
          !reconnectTimeoutRef.current &&
          reconnectCountRef.current < MAX_RECONNECTS
        ) {
          reconnectCountRef.current++
          reconnectTimeoutRef.current = setTimeout(connect, 3000)
        }
      }

      ws.onerror = () => {
        // handled via onclose; browser logs its own message regardless
      }
    } catch {
      // WebSocket not available — polling will handle updates
    }
  }, [projectId, options])

  const disconnect = useCallback(() => {
    isManuallyClosedRef.current = true
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }
    if (wsRef.current) {
      const ws = wsRef.current
      wsRef.current = null
      // Only close if past CONNECTING state — calling close() on a CONNECTING
      // socket causes an uncatchable browser console error
      if (ws.readyState !== WebSocket.CONNECTING) {
        ws.close(1000, 'User disconnected')
      }
      // If still CONNECTING, onopen will see isManuallyClosedRef and close cleanly
    }
  }, [])

  useEffect(() => {
    if (projectId) {
      isManuallyClosedRef.current = false
      reconnectCountRef.current = 0
      connect()
    }
    return () => {
      disconnect()
    }
  }, [projectId, connect, disconnect])

  const sendMessage = useCallback((message: unknown) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message))
    }
  }, [])

  return {
    sendMessage,
    disconnect,
    isConnected: wsRef.current?.readyState === WebSocket.OPEN,
  }
}
