'use client'

import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { ExternalLink, Trash2, Plus, Youtube, RefreshCw, Search, Loader2, ChevronLeft, ChevronRight, Check, Square, Copy, CopyCheck } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent } from '@/components/ui/card'
import api, { projectsApi, searchApi, YouTubeSearchResult } from '@/lib/api'
import type { Video } from '@/types'


interface VideoManagerProps {
  projectId: string
  videos: Video[]
}

function formatDuration(seconds: number | null): string {
  if (!seconds) return ''
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return m >= 60
    ? `${Math.floor(m / 60)}h ${m % 60}m`
    : `${m}:${String(s).padStart(2, '0')}`
}




export function VideoManager({ projectId, videos }: VideoManagerProps) {
  const [mode, setMode] = useState<'url' | 'search'>('url')
  const [youtubeId, setYoutubeId] = useState('')
  const [searchMode, setSearchMode] = useState<'smart' | 'direct'>('smart')
  const [searchQuery, setSearchQuery] = useState('')
  const [allSearchResults, setAllSearchResults] = useState<YouTubeSearchResult[]>([])
  const [isSearching, setIsSearching] = useState(false)
  const [searchError, setSearchError] = useState<string | null>(null)
  const [searchPage, setSearchPage] = useState(0)
  const [selectedForAdd, setSelectedForAdd] = useState<Set<string>>(new Set())
  const [addProgress, setAddProgress] = useState<{ done: number; total: number; errors: string[] } | null>(null)
  const PAGE_SIZE = 12
  const queryClient = useQueryClient()

  const addVideo = useMutation({
    mutationFn: async (id: string) => {
      const clean = id.trim().replace(/.*[?&]v=([^&]+).*/, '$1').replace(/.*youtu\.be\/([^?]+).*/, '$1')
      const res = await api.post(`/projects/${projectId}/videos`, { youtube_video_id: clean })
      return res.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['project', projectId] })
      queryClient.invalidateQueries({ queryKey: ['project-videos', projectId] })
      setYoutubeId('')
    },
  })

  const removeVideo = useMutation({
    mutationFn: async (videoId: string) => {
      await api.delete(`/projects/${projectId}/videos/${videoId}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['project', projectId] })
      queryClient.invalidateQueries({ queryKey: ['project-videos', projectId] })
    },
  })

  const retryVideo = useMutation({
    mutationFn: async (videoId: string) => projectsApi.retryVideo(projectId, videoId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['project', projectId] })
      queryClient.invalidateQueries({ queryKey: ['project-videos', projectId] })
    },
  })

  const addVideosBatch = useMutation({
    mutationFn: async (ids: string[]) => {
      const cleanId = (id: string) =>
        id.trim().replace(/.*[?&]v=([^&]+).*/, '$1').replace(/.*youtu\.be\/([^?]+).*/, '$1')

      setAddProgress({ done: 0, total: ids.length, errors: [] })
      const errors: string[] = []
      const chunkSize = 4
      const idArray = [...ids]

      for (let i = 0; i < idArray.length; i += chunkSize) {
        const chunk = idArray.slice(i, i + chunkSize)
        const results = await Promise.allSettled(
          chunk.map((id) =>
            api.post(`/projects/${projectId}/videos`, { youtube_video_id: cleanId(id) })
          )
        )
        results.forEach((r, j) => {
          if (r.status === 'rejected') {
            const errMsg = (r.reason as Error)?.message || 'Unknown error'
            errors.push(`${chunk[j]}: ${errMsg}`)
          }
        })
        setAddProgress((prev) =>
          prev
            ? { done: Math.min(i + chunkSize, ids.length), total: ids.length, errors: [...errors] }
            : null
        )
      }

      if (errors.length > 0 && errors.length === ids.length) {
        throw new Error(`All ${ids.length} videos failed to add`)
      }
    },
    onSuccess: () => {
      setAddProgress(null)
      queryClient.invalidateQueries({ queryKey: ['project', projectId] })
      queryClient.invalidateQueries({ queryKey: ['project-videos', projectId] })
      setSelectedForAdd(new Set())
    },
    onError: () => {
      queryClient.invalidateQueries({ queryKey: ['project', projectId] })
      queryClient.invalidateQueries({ queryKey: ['project-videos', projectId] })
    },
  })

  const toggleSelect = (id: string) => {
    setSelectedForAdd((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const selectAllResults = () => {
    setSelectedForAdd((prev) => {
      const next = new Set(prev)
      const allSelected = searchResults.every((v) => next.has(v.id))
      if (allSelected) {
        searchResults.forEach((v) => next.delete(v.id))
      } else {
        searchResults.forEach((v) => next.add(v.id))
      }
      return next
    })
  }

  const handleSearchVideos = async (e?: React.FormEvent) => {
    if (e) e.preventDefault()
    if (!searchQuery.trim()) return
    setIsSearching(true)
    setSearchError(null)
    setSelectedForAdd(new Set())
    try {
      const data = await searchApi.searchVideos(searchQuery, searchMode, 0, 96)
      setAllSearchResults(data.videos || [])
      setSearchPage(0)
    } catch (err) {
      setSearchError(err instanceof Error ? err.message : 'Search failed')
      setAllSearchResults([])
    } finally {
      setIsSearching(false)
    }
  }

  const handleAdd = (e: React.FormEvent) => {
    e.preventDefault()
    if (youtubeId.trim()) addVideo.mutate(youtubeId)
  }

  const existingIds = new Set(videos.map((v) => v.youtube_video_id))
  const newVideosAll = allSearchResults.filter((v) => !existingIds.has(v.id))
  const alreadyInTotal = allSearchResults.length - newVideosAll.length
  const totalPages = Math.max(1, Math.ceil(newVideosAll.length / PAGE_SIZE))
  const currentPage = Math.min(searchPage, totalPages - 1)
  const searchResults = newVideosAll.slice(currentPage * PAGE_SIZE, (currentPage + 1) * PAGE_SIZE)

  return (
    <div className="space-y-4 max-w-3xl mx-auto py-2">
      {/* Mode toggle */}
      <div className="flex gap-1 bg-muted rounded-lg p-1 w-fit">
        <button
          type="button"
          onClick={() => setMode('url')}
          className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
            mode === 'url' ? 'bg-background shadow-sm' : 'text-muted-foreground hover:text-foreground'
          }`}
        >
          URL / ID
        </button>
        <button
          type="button"
          onClick={() => setMode('search')}
          className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
            mode === 'search' ? 'bg-background shadow-sm' : 'text-muted-foreground hover:text-foreground'
          }`}
        >
          Search by term
        </button>
      </div>

      {/* Add video — URL mode */}
      {mode === 'url' && (
        <>
          <form onSubmit={handleAdd} className="flex gap-2">
            <Input
              value={youtubeId}
              onChange={(e) => setYoutubeId(e.target.value)}
              placeholder="YouTube URL or video ID (e.g. dQw4w9WgXcQ)"
              className="flex-1"
            />
            <Button type="submit" disabled={!youtubeId.trim() || addVideo.isPending}>
              <Plus className="h-4 w-4 mr-1" />
              Add
            </Button>
          </form>
          {addVideo.isError && (
            <p className="text-sm text-destructive">{(addVideo.error as Error).message}</p>
          )}
        </>
      )}

      {/* Add video — Search mode */}
      {mode === 'search' && (
        <>
          {/* Sub-toggle: Smart / Direct */}
          <div className="flex gap-1 bg-muted rounded-lg p-1 w-fit">
            <button
              type="button"
              onClick={() => setSearchMode('smart')}
              className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                searchMode === 'smart' ? 'bg-background shadow-sm' : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              Smart
            </button>
            <button
              type="button"
              onClick={() => setSearchMode('direct')}
              className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                searchMode === 'direct' ? 'bg-background shadow-sm' : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              Direct
            </button>
          </div>

          <form onSubmit={handleSearchVideos} className="flex gap-2">
            <Input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search YouTube videos (e.g. english, python tutorial...)"
              className="flex-1"
            />
            <Button type="submit" disabled={!searchQuery.trim() || isSearching}>
              {isSearching ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Search className="h-4 w-4" />
              )}
            </Button>
          </form>
          {searchError && (
            <p className="text-sm text-destructive">{searchError}</p>
          )}

          {/* Search results */}
          {allSearchResults.length > 0 && newVideosAll.length === 0 && (
            <p className="text-sm text-muted-foreground text-center py-4">
              All {allSearchResults.length} results are already in the project.
            </p>
          )}
          {searchResults.length > 0 && (
            <>
              {/* Batch actions */}
              <div className="flex items-center gap-2 flex-wrap">
                {alreadyInTotal > 0 && (
                  <span className="text-xs text-muted-foreground">
                    {alreadyInTotal} already in project
                  </span>
                )}
                <button
                  type="button"
                  onClick={selectAllResults}
                  className="text-xs text-muted-foreground hover:text-foreground transition-colors"
                >
                  {searchResults.every((v) => selectedForAdd.has(v.id)) && selectedForAdd.size > 0
                    ? 'Deselect all'
                    : 'Select all'}
                </button>
                {selectedForAdd.size > 0 && (
                  <Button
                    size="sm"
                    onClick={() => addVideosBatch.mutate([...selectedForAdd])}
                    disabled={addVideosBatch.isPending}
                  >
                    {addVideosBatch.isPending ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin mr-1" />
                    ) : (
                      <Plus className="h-3.5 w-3.5 mr-1" />
                    )}
                    {addVideosBatch.isPending && addProgress
                      ? `Adding ${addProgress.done}/${addProgress.total}...`
                      : `Add ${selectedForAdd.size} video${selectedForAdd.size !== 1 ? 's' : ''}`}
                  </Button>
                )}
                {addProgress && addProgress.errors.length > 0 && addVideosBatch.isError && (
                  <span className="text-xs text-destructive">
                    {addProgress.errors.length} error{addProgress.errors.length !== 1 ? 's' : ''}
                  </span>
                )}
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {searchResults.map((video) => {
                  const isSelected = selectedForAdd.has(video.id)
                  return (
                    <Card key={video.id} className="overflow-hidden group">
                      <div
                        className="relative aspect-video bg-muted cursor-pointer"
                        onClick={() => toggleSelect(video.id)}
                      >
                        <img
                          src={video.thumbnail_url}
                          alt={video.title}
                          className="w-full h-full object-cover"
                        />
                        <div className={`absolute inset-0 transition-colors ${
                          isSelected
                            ? 'bg-primary/30 border-2 border-primary'
                            : 'bg-transparent group-hover:bg-black/10'
                        }`}>
                          <div className={`absolute top-2 right-2 w-6 h-6 rounded-full flex items-center justify-center transition-opacity ${
                            isSelected
                              ? 'bg-primary text-primary-foreground opacity-100'
                              : 'bg-black/40 text-white opacity-0 group-hover:opacity-100'
                          }`}>
                            {isSelected ? (
                              <Check className="h-4 w-4" />
                            ) : (
                              <Square className="h-4 w-4" />
                            )}
                          </div>
                        </div>
                        <div className="absolute bottom-1.5 right-1.5 bg-black/80 text-white text-xs px-1.5 py-0.5 rounded">
                          {formatDuration(video.duration_seconds)}
                        </div>
                      </div>
                      <CardContent className="p-2">
                        <p className="text-sm font-medium line-clamp-2">{video.title}</p>
                        <p className="text-xs text-muted-foreground mt-1">{video.channel}</p>
                        <div className="mt-2">
                          <Button
                            size="sm"
                            variant={isSelected ? 'default' : 'outline'}
                            className="w-full"
                            onClick={() => toggleSelect(video.id)}
                          >
                            {isSelected ? (
                              <>
                                <Check className="h-3 w-3 mr-1" />
                                Selected
                              </>
                            ) : (
                              <>
                                <Plus className="h-3 w-3 mr-1" />
                                Select
                              </>
                            )}
                          </Button>
                        </div>
                      </CardContent>
                    </Card>
                  )
                })}
              </div>

              {/* Pagination */}
              {newVideosAll.length > PAGE_SIZE && (
                <div className="flex items-center justify-center gap-3 pt-2">
                  <button
                    type="button"
                    onClick={() => setSearchPage(p => p - 1)}
                    disabled={currentPage === 0}
                    className="inline-flex items-center gap-1 rounded-md text-sm font-medium h-8 px-3 border hover:bg-accent disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    <ChevronLeft className="h-4 w-4" />
                  </button>
                  <span className="text-sm text-muted-foreground">
                    {currentPage + 1} / {totalPages}
                  </span>
                  <button
                    type="button"
                    onClick={() => setSearchPage(p => p + 1)}
                    disabled={currentPage + 1 >= totalPages}
                    className="inline-flex items-center gap-1 rounded-md text-sm font-medium h-8 px-3 border hover:bg-accent disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    <ChevronRight className="h-4 w-4" />
                  </button>
                </div>
              )}
            </>
          )}
        </>
      )}

      {/* Video list header */}
      {videos.length > 0 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-gray-500">{videos.length} video{videos.length !== 1 ? 's' : ''}</p>
          <CopyAllLinksButton videos={videos} />
        </div>
      )}

      {/* Video rows */}
      {videos.length === 0 ? (
        <div className="text-center py-16 text-gray-400">
          <Youtube className="h-12 w-12 mx-auto mb-3 opacity-20" />
          <p className="text-sm">No videos in project yet.</p>
        </div>
      ) : (
        <div className="divide-y divide-gray-100 border border-gray-200 rounded-xl overflow-hidden">
          {videos.map((video) => (
            <VideoRow
              key={video.id}
              video={video}
              onRetry={() => retryVideo.mutate(video.id)}
              onRemove={() => removeVideo.mutate(video.id)}
              isRetrying={retryVideo.isPending}
              isRemoving={removeVideo.isPending}
            />
          ))}
        </div>
      )}
    </div>
  )
}

interface VideoRowProps {
  video: Video
  onRetry: () => void
  onRemove: () => void
  isRetrying: boolean
  isRemoving: boolean
}

function VideoRow({ video, onRetry, onRemove, isRetrying, isRemoving }: VideoRowProps) {
  const [menuOpen, setMenuOpen] = useState(false)
  const title = video.title || video.youtube_video_id
  const ytUrl = `https://www.youtube.com/watch?v=${video.youtube_video_id}`

  const statusBadge = () => {
    if (video.status === 'completed') return (
      <span className="inline-flex items-center gap-1 text-xs font-medium text-green-700 bg-green-100 px-2.5 py-0.5 rounded-full">
        <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
        Ready
      </span>
    )
    if (video.status === 'processing') return (
      <span className="inline-flex items-center gap-1 text-xs font-medium text-orange-700 bg-orange-100 px-2.5 py-0.5 rounded-full">
        <Loader2 className="h-3 w-3 animate-spin" />
        Processing
      </span>
    )
    if (video.status === 'failed') return (
      <span className="inline-flex items-center gap-1 text-xs font-medium text-red-700 bg-red-100 px-2.5 py-0.5 rounded-full">
        <span className="w-1.5 h-1.5 rounded-full bg-red-500" />
        Failed
      </span>
    )
    return (
      <span className="inline-flex items-center gap-1 text-xs font-medium text-gray-600 bg-gray-100 px-2.5 py-0.5 rounded-full">
        <span className="w-1.5 h-1.5 rounded-full bg-gray-400" />
        Pending
      </span>
    )
  }

  return (
    <div className="flex items-center gap-4 px-5 py-4 bg-white hover:bg-gray-50 transition-colors">
      {/* Thumbnail */}
      <div className="flex-shrink-0 relative w-28 h-16 rounded-lg overflow-hidden bg-gray-100">
        {video.thumbnail_url ? (
          <img src={video.thumbnail_url} alt={title} className="w-full h-full object-cover" />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <Youtube className="h-5 w-5 text-gray-300" />
          </div>
        )}
        {video.duration && (
          <div className="absolute bottom-1 right-1 bg-black/80 text-white text-[10px] px-1.5 py-0.5 rounded font-mono">
            {formatDuration(video.duration)}
          </div>
        )}
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0">
        <a href={ytUrl} target="_blank" rel="noopener noreferrer"
          className="font-medium text-sm text-gray-900 hover:underline line-clamp-1">
          {title}
        </a>
        {video.channel_title && (
          <p className="text-xs text-gray-500 mt-0.5">{video.channel_title}</p>
        )}
        {video.error_message && video.status === 'failed' && (
          <p className="text-xs text-red-500 mt-0.5 truncate" title={video.error_message}>{video.error_message}</p>
        )}
      </div>

      {/* Status badge */}
      <div className="flex-shrink-0">{statusBadge()}</div>

      {/* 3-dot menu */}
      <div className="relative flex-shrink-0">
        <button
          type="button"
          onClick={() => setMenuOpen(!menuOpen)}
          className="p-1.5 rounded-md text-gray-400 hover:text-gray-700 hover:bg-gray-100 transition-colors"
        >
          <svg className="h-4 w-4" viewBox="0 0 16 16" fill="currentColor">
            <circle cx="8" cy="3" r="1.5" /><circle cx="8" cy="8" r="1.5" /><circle cx="8" cy="13" r="1.5" />
          </svg>
        </button>
        {menuOpen && (
          <>
            <div className="fixed inset-0 z-10" onClick={() => setMenuOpen(false)} />
            <div className="absolute right-0 top-full mt-1 z-20 bg-white border border-gray-200 rounded-lg shadow-md py-1 min-w-[140px]">
              <a href={ytUrl} target="_blank" rel="noopener noreferrer" onClick={() => setMenuOpen(false)}
                className="flex items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50">
                <ExternalLink className="h-3.5 w-3.5" /> Open on YouTube
              </a>
              {(video.status === 'failed' || video.status === 'pending') && (
                <button type="button" disabled={isRetrying}
                  onClick={() => { setMenuOpen(false); onRetry() }}
                  className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50">
                  <RefreshCw className="h-3.5 w-3.5" /> Retry
                </button>
              )}
              <button type="button" disabled={isRemoving}
                onClick={() => { setMenuOpen(false); onRemove() }}
                className="w-full flex items-center gap-2 px-3 py-2 text-sm text-red-600 hover:bg-red-50">
                <Trash2 className="h-3.5 w-3.5" /> Remove
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

function CopyAllLinksButton({ videos }: { videos: Video[] }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    const links = videos
      .map((v) => `https://www.youtube.com/watch?v=${v.youtube_video_id}`)
      .join('\n')
    await navigator.clipboard.writeText(links)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <Button variant="outline" size="sm" onClick={handleCopy}>
      {copied ? (
        <CopyCheck className="h-3.5 w-3.5 mr-1.5" />
      ) : (
        <Copy className="h-3.5 w-3.5 mr-1.5" />
      )}
      {copied ? 'Copied!' : `Copy ${videos.length} link${videos.length !== 1 ? 's' : ''}`}
    </Button>
  )
}
