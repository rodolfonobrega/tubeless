'use client'

import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Send, Bot, ExternalLink, Clock, ChevronDown, ChevronUp, Check, Video as VideoIcon } from 'lucide-react'
import { formatTimestamp, getVideoDisplayTitle, getYouTubeId } from '@/lib/utils'
import type { ChatMessage, ChatSource, Video } from '@/types'

interface ChatContainerProps {
  messages: ChatMessage[]
  videos?: Video[]
  onSendMessage: (message: string, videoIds?: string[]) => void
  isLoading?: boolean
  isStreaming?: boolean
  className?: string
}

export function ChatContainer({
  messages,
  videos = [],
  onSendMessage,
  isLoading = false,
  isStreaming = false,
}: ChatContainerProps) {
  const [input, setInput] = useState('')
  const [selectedVideoIds, setSelectedVideoIds] = useState<string[]>([])
  const [hasInitialized, setHasInitialized] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)

  useEffect(() => {
    if (videos.length > 0 && !hasInitialized) {
      setSelectedVideoIds(videos.map((v) => v.youtube_video_id))
      setHasInitialized(true)
    }
  }, [videos, hasInitialized])

  const scrollRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const dropdownRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages, isStreaming])

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (input.trim() && !isLoading) {
      const passedIds = selectedVideoIds.length > 0 ? selectedVideoIds : undefined
      onSendMessage(input.trim(), passedIds)
      setInput('')
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto'
      }
    }
  }

  const allSelected = selectedVideoIds.length === videos.length
  const noneSelected = selectedVideoIds.length === 0

  const toggleVideo = (youtubeId: string) => {
    setSelectedVideoIds((prev) => {
      if (prev.includes(youtubeId)) {
        return prev.filter((id) => id !== youtubeId)
      } else {
        return [...prev, youtubeId]
      }
    })
  }

  const handleSelectAll = () => {
    setSelectedVideoIds(videos.map((v) => v.youtube_video_id))
  }

  const handleDeselectAll = () => {
    setSelectedVideoIds([])
  }

  const handleInvert = () => {
    setSelectedVideoIds((prev) =>
      videos.map((v) => v.youtube_video_id).filter((id) => !prev.includes(id))
    )
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value)
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 160)}px`
    }
  }

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-6 py-5">
        <div className={`max-w-6xl mx-auto w-full min-h-full flex flex-col ${messages.length === 0 ? 'justify-center' : 'justify-start space-y-5'}`}>
          <AnimatePresence>
            {messages.length === 0 ? (
              <motion.div
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex flex-col items-center justify-center text-center"
              >
                <div className="w-12 h-12 rounded-full bg-gray-100 flex items-center justify-center mb-3">
                  <Bot className="h-6 w-6 text-gray-400" />
                </div>
                <h3 className="text-base font-semibold text-gray-900 mb-1">Ask anything about your project</h3>
                <p className="text-sm text-gray-500">Get answers with citations from video transcripts</p>
              </motion.div>
            ) : (
              messages.map((message) => (
                <MessageBubble key={message.id} message={message} />
              ))
            )}

            {/* Streaming indicator */}
            {(isLoading || isStreaming) && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex gap-3"
              >
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center">
                  <Bot className="h-4 w-4 text-gray-400" />
                </div>
                <div className="flex items-center gap-1 px-4 py-3 bg-white border border-gray-200 rounded-2xl rounded-tl-sm">
                  <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                  <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '120ms' }} />
                  <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '240ms' }} />
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* Input */}
      <div className="border-t border-gray-200 bg-white px-6 py-4">
        <form onSubmit={handleSubmit} className="max-w-6xl mx-auto w-full space-y-3 relative">
          {/* Video filter dropdown */}
          {videos.length > 1 && (
            <div className="relative" ref={dropdownRef}>
              <button
                type="button"
                onClick={() => setMenuOpen(!menuOpen)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-gray-200 bg-white hover:bg-gray-50 text-xs font-semibold text-gray-700 transition-colors shadow-sm focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent"
              >
                <VideoIcon className="h-3.5 w-3.5 text-gray-500" />
                <span>
                  {allSelected
                    ? 'Active Sources: All videos'
                    : noneSelected
                      ? 'Active Sources: No videos selected'
                      : `Active Sources: ${selectedVideoIds.length} of ${videos.length} selected`}
                </span>
                {menuOpen ? <ChevronUp className="h-3 w-3 text-gray-400 ml-1" /> : <ChevronDown className="h-3 w-3 text-gray-400 ml-1" />}
              </button>

              {menuOpen && (
                <div className="absolute bottom-full mb-2 left-0 z-10 w-80 bg-white border border-gray-200 shadow-lg rounded-xl py-1.5 max-h-64 overflow-y-auto focus:outline-none">
                  <div className="px-3 py-1.5 border-b border-gray-100">
                    <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Select Active Sources</p>
                  </div>

                  <div className="flex items-center gap-1.5 px-3 py-2 border-b border-gray-100">
                    <button
                      type="button"
                      onClick={handleSelectAll}
                      className="text-[10px] font-semibold px-2 py-1 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded transition-colors"
                    >
                      Select All
                    </button>
                    <button
                      type="button"
                      onClick={handleDeselectAll}
                      className="text-[10px] font-semibold px-2 py-1 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded transition-colors"
                    >
                      Deselect All
                    </button>
                    <button
                      type="button"
                      onClick={handleInvert}
                      className="text-[10px] font-semibold px-2 py-1 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded transition-colors"
                    >
                      Invert
                    </button>
                  </div>

                  {videos.map((v) => {
                    const isSelected = selectedVideoIds.includes(v.youtube_video_id)
                    const displayTitle = getVideoDisplayTitle(v.title, v.youtube_video_id)
                    const thumbUrl = v.thumbnail_url || `https://img.youtube.com/vi/${v.youtube_video_id}/mqdefault.jpg`
                    return (
                      <button
                        key={v.id}
                        type="button"
                        onClick={() => toggleVideo(v.youtube_video_id)}
                        title={displayTitle}
                        className="w-full flex items-center justify-between px-3 py-2 text-left text-xs text-gray-700 hover:bg-gray-50 transition-colors"
                      >
                        <div className="flex items-center gap-2 min-w-0 flex-1">
                          <div className="w-8 h-6 rounded overflow-hidden flex-shrink-0 bg-gray-100 border border-gray-200">
                            <img src={thumbUrl} alt="" className="w-full h-full object-cover" />
                          </div>
                          <span className="truncate pr-4">{displayTitle}</span>
                        </div>
                        {isSelected && <Check className="h-3.5 w-3.5 text-indigo-600 flex-shrink-0" />}
                      </button>
                    )
                  })}
                </div>
              )}
            </div>
          )}

          <div className="flex gap-2 items-end">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={handleInput}
              onKeyDown={handleKeyDown}
              placeholder="Ask anything about your project..."
              rows={1}
              disabled={isLoading || isStreaming}
              className="flex-1 resize-none min-h-[44px] max-h-40 px-4 py-3 text-sm border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent disabled:opacity-50 bg-white"
            />
            <button
              type="submit"
              disabled={!input.trim() || isLoading || isStreaming}
              className="flex-shrink-0 w-10 h-10 flex items-center justify-center rounded-xl bg-gray-900 text-white hover:bg-gray-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              <Send className="h-4 w-4" />
            </button>
          </div>
          <p className="text-xs text-gray-400">Press ↵ to send, Shift + ↵ for new line</p>
        </form>
      </div>
    </div>
  )
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === 'user'
  const [sourcesOpen, setSourcesOpen] = useState(false)
  const timeLabel = message.created_at
    ? new Date(message.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : ''

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}
    >
      {isUser ? (
        /* User bubble — dark, right side */
        <div className="max-w-[75%]">
          <div className="bg-gray-900 text-white px-4 py-3 rounded-2xl rounded-tr-sm text-sm">
            {message.content}
          </div>
          <div className="flex justify-end mt-1">
            <span className="text-xs text-gray-400">{timeLabel} ✓</span>
          </div>
        </div>
      ) : (
        /* AI response — white card with border, left side */
        <div className="max-w-[85%] space-y-2">
          <div className="bg-white border border-gray-200 rounded-2xl rounded-tl-sm px-5 py-4">
            <div className="text-sm text-gray-800 leading-relaxed prose-sm">
              <MarkdownContent content={message.content} sources={message.sources} />
            </div>

            {/* Sources collapsible */}
            {message.sources && message.sources.length > 0 && (
              <div className="mt-3 pt-3 border-t border-gray-100">
                <button
                  type="button"
                  onClick={() => setSourcesOpen(!sourcesOpen)}
                  className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-700 transition-colors"
                >
                  {sourcesOpen ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
                  Sources ({message.sources.length})
                </button>
                {sourcesOpen && (
                  <div className="mt-2 flex flex-wrap gap-2">
                    {message.sources.map((source, i) => (
                      <SourceChip key={i} source={source} index={i + 1} />
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
          <div className="ml-1">
            <span className="text-xs text-gray-400">{timeLabel}</span>
          </div>
        </div>
      )}
    </motion.div>
  )
}

function SourceChip({ source, index }: { source: ChatSource; index: number }) {
  const href = source.youtube_url || `https://www.youtube.com/watch?v=${source.video_id}`
  const thumbnailId = source.video_id ? getYouTubeId(source.video_id) : source.video_id
  const displayTitle = getVideoDisplayTitle(source.video_title, source.video_id)

  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg border border-gray-200 hover:bg-gray-50 transition-colors group"
    >
      {thumbnailId && (
        <div className="w-10 h-7 rounded overflow-hidden flex-shrink-0 bg-gray-100">
          <img
            src={`https://img.youtube.com/vi/${thumbnailId}/mqdefault.jpg`}
            alt={source.video_title || ''}
            className="w-full h-full object-cover"
          />
        </div>
      )}
      <div className="min-w-0">
        <p className="text-xs font-medium text-gray-700 truncate max-w-[150px]">
          {displayTitle}
        </p>
        {source.timestamp != null && (
          <p className="text-[10px] text-gray-400 flex items-center gap-0.5">
            <Clock className="h-2.5 w-2.5" />
            {formatTimestamp(source.timestamp)}
          </p>
        )}
      </div>
      <ExternalLink className="h-3 w-3 text-gray-300 group-hover:text-gray-500 flex-shrink-0" />
    </a>
  )
}

function MarkdownContent({ content, sources = [] }: { content: string; sources?: ChatSource[] }) {
  const htmlContent = content
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/```([\s\S]*?)```/g, '<pre class="bg-gray-50 border border-gray-200 p-3 rounded-lg my-2 overflow-x-auto text-xs"><code>$1</code></pre>')
    .replace(/`(.*?)`/g, '<code class="bg-gray-100 px-1 py-0.5 rounded text-xs font-mono">$1</code>')
    .replace(/^### (.*$)/gm, '<h3 class="text-base font-semibold mt-3 mb-1 text-gray-900">$1</h3>')
    .replace(/^## (.*$)/gm, '<h2 class="text-lg font-semibold mt-4 mb-1 text-gray-900">$1</h2>')
    .replace(/^\- (.*$)/gm, '<li class="ml-4 list-disc text-gray-700">$1</li>')
    .replace(/^\d+\. (.*$)/gm, '<li class="ml-4 list-decimal text-gray-700">$1</li>')
    .replace(/\[Fonte\s+(\d+)\]/gi, (_, n) => {
      const idx = parseInt(n, 10) - 1
      const source = sources[idx]
      const href = source
        ? (source.youtube_url || `https://www.youtube.com/watch?v=${source.video_id}`)
        : '#'
      return `<a href="${href}" target="_blank" rel="noopener noreferrer" class="inline-flex items-center text-indigo-600 hover:underline font-medium text-xs px-1 py-0.5 bg-indigo-50 rounded">[${n}]</a>`
    })
    .replace(/\n\n/g, '</p><p class="mt-2 text-gray-700">')
    .replace(/\n/g, '<br />')

  return <p dangerouslySetInnerHTML={{ __html: htmlContent }} />
}
