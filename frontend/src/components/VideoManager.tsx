'use client'

import { useEffect, useState, type FormEvent } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import {
  ExternalLink,
  Trash2,
  Plus,
  Youtube,
  RefreshCw,
  Search,
  Loader2,
  ChevronLeft,
  ChevronRight,
  Check,
  Square,
  Copy,
  CopyCheck,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent } from '@/components/ui/card'
import { getVideoDisplayTitle } from '@/lib/utils'
import api, { projectsApi, searchApi, YouTubeSearchResult } from '@/lib/api'
import type { Video } from '@/types'

interface VideoManagerProps {
  projectId: string
  videos: Video[]
}

function formatDuration(seconds: number | null): string {
  if (!seconds) return ''
  const minutes = Math.floor(seconds / 60)
  const secs = seconds % 60
  return minutes >= 60
    ? `${Math.floor(minutes / 60)}h ${minutes % 60}m`
    : `${minutes}:${String(secs).padStart(2, '0')}`
}

export function VideoManager({ projectId, videos }: VideoManagerProps) {
  const [showAddPanel, setShowAddPanel] = useState(videos.length === 0)
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

  useEffect(() => {
    if (videos.length === 0) {
      setShowAddPanel(true)
    }
  }, [videos.length])

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

  const retryFailed = useMutation({
    mutationFn: async () => projectsApi.retryAll(projectId),
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
        results.forEach((result, index) => {
          if (result.status === 'rejected') {
            const errMsg = (result.reason as Error)?.message || 'Unknown error'
            errors.push(`${chunk[index]}: ${errMsg}`)
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
      const allSelected = searchResults.every((video) => next.has(video.id))
      if (allSelected) {
        searchResults.forEach((video) => next.delete(video.id))
      } else {
        searchResults.forEach((video) => next.add(video.id))
      }
      return next
    })
  }

  const handleSearchVideos = async (event?: FormEvent) => {
    if (event) event.preventDefault()
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

  const handleAdd = (event: FormEvent) => {
    event.preventDefault()
    if (youtubeId.trim()) addVideo.mutate(youtubeId)
  }

  const existingIds = new Set(videos.map((video) => video.youtube_video_id))
  const newVideosAll = allSearchResults.filter((video) => !existingIds.has(video.id))
  const alreadyInTotal = allSearchResults.length - newVideosAll.length
  const totalPages = Math.max(1, Math.ceil(newVideosAll.length / PAGE_SIZE))
  const currentPage = Math.min(searchPage, totalPages - 1)
  const searchResults = newVideosAll.slice(currentPage * PAGE_SIZE, (currentPage + 1) * PAGE_SIZE)

  const failedVideos = videos.filter((video) => video.status === 'failed')
  const completedVideos = videos.filter((video) => video.status === 'completed')
  const processingVideos = videos.filter((video) => video.status === 'processing')
  const queuedVideos = videos.filter((video) => video.status === 'pending')

  return (
    <div className="space-y-4 max-w-5xl mx-auto py-2">
      <div className="rounded-2xl border border-gray-200 bg-white shadow-sm">
        <div className="flex flex-col gap-4 border-b border-gray-100 px-5 py-5 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-xl font-semibold text-gray-900">Videos</h2>
              <span className="rounded-full bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-600">
                {videos.length} total
              </span>
              {processingVideos.length > 0 && (
                <span className="rounded-full bg-indigo-50 px-2.5 py-1 text-xs font-medium text-indigo-700">
                  {processingVideos.length} active
                </span>
              )}
              {queuedVideos.length > 0 && (
                <span className="rounded-full bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-700">
                  {queuedVideos.length} queued
                </span>
              )}
              {failedVideos.length > 0 && (
                <span className="rounded-full bg-red-50 px-2.5 py-1 text-xs font-medium text-red-700">
                  {failedVideos.length} failed
                </span>
              )}
            </div>
            <p className="mt-1 text-sm text-gray-500">
              Browse your library, add new videos in a separate panel, and retry failed items without changing tabs.
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            {failedVideos.length > 0 && (
              <Button
                type="button"
                variant="outline"
                onClick={() => retryFailed.mutate()}
                disabled={retryFailed.isPending}
              >
                {retryFailed.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin mr-1" />
                ) : (
                  <RefreshCw className="h-4 w-4 mr-1" />
                )}
                Retry failed ({failedVideos.length})
              </Button>
            )}
            <Button type="button" onClick={() => setShowAddPanel((value) => !value)}>
              <Plus className="h-4 w-4 mr-1" />
              {showAddPanel ? 'Close add panel' : 'Add videos'}
            </Button>
          </div>
        </div>

        {showAddPanel && (
          <div className="border-b border-gray-100 bg-gray-50/60 px-5 py-5">
            <div className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                <div>
                  <div className="text-sm font-semibold text-gray-900">Add videos to this project</div>
                  <p className="mt-1 text-sm text-gray-500">
                    Use a direct URL or search YouTube and queue several videos at once.
                  </p>
                </div>

                <div className="flex gap-1 rounded-lg bg-muted p-1 w-fit">
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
              </div>

              {mode === 'url' && (
                <form onSubmit={handleAdd} className="mt-4 flex gap-2">
                  <Input
                    value={youtubeId}
                    onChange={(event) => setYoutubeId(event.target.value)}
                    placeholder="YouTube URL or video ID (e.g. dQw4w9WgXcQ)"
                    className="flex-1"
                  />
                  <Button type="submit" disabled={!youtubeId.trim() || addVideo.isPending}>
                    <Plus className="h-4 w-4 mr-1" />
                    Add
                  </Button>
                </form>
              )}

              {mode === 'search' && (
                <div className="mt-4 space-y-4">
                  <div className="flex gap-1 rounded-lg bg-muted p-1 w-fit">
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
                      onChange={(event) => setSearchQuery(event.target.value)}
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

                  {searchError && <p className="text-sm text-destructive">{searchError}</p>}

                  {allSearchResults.length > 0 && newVideosAll.length === 0 && (
                    <p className="text-sm text-muted-foreground text-center py-4">
                      All {allSearchResults.length} results are already in the project.
                    </p>
                  )}

                  {searchResults.length > 0 && (
                    <>
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
                          {searchResults.every((video) => selectedForAdd.has(video.id)) && selectedForAdd.size > 0
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

                      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
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
                                  className="h-full w-full object-cover"
                                />
                                <div
                                  className={`absolute inset-0 transition-colors ${
                                    isSelected
                                      ? 'bg-primary/30 border-2 border-primary'
                                      : 'bg-transparent group-hover:bg-black/10'
                                  }`}
                                >
                                  <div
                                    className={`absolute top-2 right-2 flex h-6 w-6 items-center justify-center rounded-full transition-opacity ${
                                      isSelected
                                        ? 'bg-primary text-primary-foreground opacity-100'
                                        : 'bg-black/40 text-white opacity-0 group-hover:opacity-100'
                                    }`}
                                  >
                                    {isSelected ? (
                                      <Check className="h-4 w-4" />
                                    ) : (
                                      <Square className="h-4 w-4" />
                                    )}
                                  </div>
                                </div>
                                <div className="absolute bottom-1.5 right-1.5 rounded bg-black/80 px-1.5 py-0.5 text-xs text-white">
                                  {formatDuration(video.duration_seconds)}
                                </div>
                              </div>
                              <CardContent className="p-2">
                                <p className="text-sm font-medium line-clamp-2">{video.title}</p>
                                <p className="mt-1 text-xs text-muted-foreground">{video.channel}</p>
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

                      {newVideosAll.length > PAGE_SIZE && (
                        <div className="flex items-center justify-center gap-3 pt-2">
                          <button
                            type="button"
                            onClick={() => setSearchPage((page) => page - 1)}
                            disabled={currentPage === 0}
                            className="inline-flex items-center gap-1 rounded-md border px-3 h-8 text-sm font-medium hover:bg-accent disabled:cursor-not-allowed disabled:opacity-40"
                          >
                            <ChevronLeft className="h-4 w-4" />
                          </button>
                          <span className="text-sm text-muted-foreground">
                            {currentPage + 1} / {totalPages}
                          </span>
                          <button
                            type="button"
                            onClick={() => setSearchPage((page) => page + 1)}
                            disabled={currentPage + 1 >= totalPages}
                            className="inline-flex items-center gap-1 rounded-md border px-3 h-8 text-sm font-medium hover:bg-accent disabled:cursor-not-allowed disabled:opacity-40"
                          >
                            <ChevronRight className="h-4 w-4" />
                          </button>
                        </div>
                      )}
                    </>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {videos.length > 0 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-gray-500">
            {completedVideos.length} completed, {failedVideos.length} failed
          </p>
          <CopyAllLinksButton videos={videos} />
        </div>
      )}

      {videos.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-gray-200 bg-white py-16 text-center text-gray-400">
          <Youtube className="mx-auto mb-3 h-12 w-12 opacity-20" />
          <p className="text-sm">No videos in project yet.</p>
        </div>
      ) : (
        <div className="overflow-hidden rounded-2xl border border-gray-200">
          <div className="divide-y divide-gray-100">
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
  const title = getVideoDisplayTitle(video.title, video.youtube_video_id)
  const ytUrl = `https://www.youtube.com/watch?v=${video.youtube_video_id}`

  const statusBadge = () => {
    if (video.status === 'completed') {
      return (
        <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-medium text-green-700">
          <span className="h-1.5 w-1.5 rounded-full bg-green-500" />
          Ready
        </span>
      )
    }
    if (video.status === 'processing') {
      return (
        <span className="inline-flex items-center gap-1 rounded-full bg-indigo-100 px-2.5 py-0.5 text-xs font-medium text-indigo-700">
          <Loader2 className="h-3 w-3 animate-spin" />
          Processing
        </span>
      )
    }
    if (video.status === 'failed') {
      return (
        <span className="inline-flex items-center gap-1 rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-medium text-red-700">
          <span className="h-1.5 w-1.5 rounded-full bg-red-500" />
          Failed
        </span>
      )
    }
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-medium text-amber-700">
        <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
        Queued
      </span>
    )
  }

  return (
    <div className="flex items-center gap-4 bg-white px-5 py-4 transition-colors hover:bg-gray-50">
      <div className="relative h-16 w-28 flex-shrink-0 overflow-hidden rounded-lg bg-gray-100">
        {video.thumbnail_url ? (
          <img src={video.thumbnail_url} alt={title} className="h-full w-full object-cover" />
        ) : (
          <div className="flex h-full w-full items-center justify-center">
            <Youtube className="h-5 w-5 text-gray-300" />
          </div>
        )}
        {video.duration && (
          <div className="absolute bottom-1 right-1 rounded bg-black/80 px-1.5 py-0.5 font-mono text-[10px] text-white">
            {formatDuration(video.duration)}
          </div>
        )}
      </div>

      <div className="min-w-0 flex-1">
        <a
          href={ytUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="line-clamp-1 text-sm font-medium text-gray-900 hover:underline"
        >
          {title}
        </a>
        {video.channel_title && <p className="mt-0.5 text-xs text-gray-500">{video.channel_title}</p>}
        {video.error_message && video.status === 'failed' && (
          <p className="mt-0.5 truncate text-xs text-red-500" title={video.error_message}>
            {video.error_message}
          </p>
        )}
      </div>

      <div className="flex-shrink-0">{statusBadge()}</div>

      <div className="relative flex-shrink-0">
        <button
          type="button"
          onClick={() => setMenuOpen(!menuOpen)}
          className="rounded-md p-1.5 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-700"
        >
          <svg className="h-4 w-4" viewBox="0 0 16 16" fill="currentColor">
            <circle cx="8" cy="3" r="1.5" />
            <circle cx="8" cy="8" r="1.5" />
            <circle cx="8" cy="13" r="1.5" />
          </svg>
        </button>
        {menuOpen && (
          <>
            <div className="fixed inset-0 z-10" onClick={() => setMenuOpen(false)} />
            <div className="absolute right-0 top-full z-20 mt-1 min-w-[160px] rounded-lg border border-gray-200 bg-white py-1 shadow-md">
              <a
                href={ytUrl}
                target="_blank"
                rel="noopener noreferrer"
                onClick={() => setMenuOpen(false)}
                className="flex items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50"
              >
                <ExternalLink className="h-3.5 w-3.5" />
                Open on YouTube
              </a>
              {(video.status === 'failed' || video.status === 'pending') && (
                <button
                  type="button"
                  disabled={isRetrying}
                  onClick={() => {
                    setMenuOpen(false)
                    onRetry()
                  }}
                  className="flex w-full items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50"
                >
                  <RefreshCw className="h-3.5 w-3.5" />
                  Retry
                </button>
              )}
              <button
                type="button"
                disabled={isRemoving}
                onClick={() => {
                  setMenuOpen(false)
                  onRemove()
                }}
                className="flex w-full items-center gap-2 px-3 py-2 text-sm text-red-600 hover:bg-red-50"
              >
                <Trash2 className="h-3.5 w-3.5" />
                Remove
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
      .map((video) => `https://www.youtube.com/watch?v=${video.youtube_video_id}`)
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
