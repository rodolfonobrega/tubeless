'use client'

import { useCallback, useRef, useEffect, useState } from 'react'
import { useRouter, useParams } from 'next/navigation'
import { useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { ArrowLeft, RefreshCw, Trash2, AlertTriangle, X, FileText, Video, MessageSquare, BookOpen, Plus, Calendar, MoreHorizontal } from 'lucide-react'
import Link from 'next/link'
import { AppHeader } from '@/components/AppHeader'
import { ProcessingPipeline } from '@/components/ProcessingPipeline'
import { ConsolidatedView } from '@/components/ConsolidatedView'
import { VideoSummaryList } from '@/components/VideoSummaryCard'
import { ChatContainer } from '@/components/ChatContainer'
import { VideoManager } from '@/components/VideoManager'
import { useProject, useSynthesis, useSummaries, useChatMessages, useDeleteProject } from '@/hooks/use-project'
import { useWebSocket } from '@/hooks/use-websocket'
import { useProjectStore } from '@/stores/project-store'
import { projectsApi } from '@/lib/api'
import { cn, formatDate } from '@/lib/utils'

const SIDEBAR_TABS = [
  { value: 'videos', label: 'Videos', icon: Video },
  { value: 'chat', label: 'Chat', icon: MessageSquare },
  { value: 'synthesis', label: 'Synthesis', icon: FileText },
  { value: 'summaries', label: 'Summaries', icon: BookOpen },
] as const

type TabValue = typeof SIDEBAR_TABS[number]['value']

export default function ProjectPage() {
  const params = useParams()
  const router = useRouter()
  const projectId = params.id as string
  const queryClient = useQueryClient()

  const activeTab = useProjectStore((s) => s.activeTab) as TabValue
  const setActiveTab = useProjectStore((s) => s.setActiveTab)
  const setProcessingStatus = useProjectStore((s) => s.setProcessingStatus)
  const { project, videos, status, isLoading, isError } = useProject(projectId)

  const isProcessing = ['pending', 'processing', 'fetching', 'embedding'].includes(project?.status ?? '')
  const isFailed = project?.status === 'failed'
  const isCompleted = project?.status === 'completed'
  const isDone = isCompleted || isFailed

  const [retrying, setRetrying] = useState(false)
  const [errorBannerDismissed, setErrorBannerDismissed] = useState(false)

  const { synthesis, isLoading: synthesisLoading } = useSynthesis(isDone ? projectId : null)
  const { summaries, isLoading: summariesLoading } = useSummaries(isDone ? projectId : null)
  const { messages, sendMessage, isSending } = useChatMessages(projectId)
  const deleteProject = useDeleteProject()

  const onStatusUpdate = useCallback((data: Parameters<typeof setProcessingStatus>[0]) => {
    setProcessingStatus(data)
  }, [setProcessingStatus])

  const onComplete = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['project', projectId] })
    queryClient.invalidateQueries({ queryKey: ['project-videos', projectId] })
  }, [queryClient, projectId])

  const onError = useCallback((message: string) => {
    console.error('Processing error:', message)
  }, [])

  useWebSocket(isProcessing ? projectId : null, { onStatusUpdate, onComplete, onError })

  const prevProcessingRef = useRef(isProcessing)
  useEffect(() => {
    if (prevProcessingRef.current && isDone) {
      queryClient.invalidateQueries({ queryKey: ['project', projectId] })
      queryClient.invalidateQueries({ queryKey: ['project-videos', projectId] })
    }
    prevProcessingRef.current = isProcessing
  }, [isProcessing, isDone, queryClient, projectId])

  useEffect(() => {
    setErrorBannerDismissed(false)
    setRetrying(false)
  }, [project?.status])

  const handleDelete = async () => {
    if (confirm('Are you sure you want to delete this project?')) {
      try {
        await deleteProject.mutateAsync(projectId)
        router.push('/projects')
      } catch (err) {
        alert(err instanceof Error ? err.message : 'Failed to delete project')
      }
    }
  }

  const handleRetry = async () => {
    setRetrying(true)
    try {
      await projectsApi.retryAll(projectId)
      queryClient.invalidateQueries({ queryKey: ['project', projectId] })
      queryClient.invalidateQueries({ queryKey: ['project-videos', projectId] })
      setProcessingStatus(null)
    } catch {
      setRetrying(false)
    }
  }

  if (isError) {
    return (
      <div className="min-h-screen bg-white">
        <AppHeader />
        <div className="flex items-center justify-center min-h-[60vh]">
          <div className="text-center max-w-sm">
            <h2 className="text-xl font-semibold text-gray-900 mb-2">Project Not Found</h2>
            <p className="text-gray-500 text-sm mb-6">
              The project you're looking for doesn't exist or you don't have access to it.
            </p>
            <Link
              href="/projects"
              className="inline-flex items-center gap-2 bg-gray-900 text-white text-sm font-medium px-5 py-2.5 rounded-md hover:bg-gray-700 transition-colors"
            >
              Go Back to Projects
            </Link>
          </div>
        </div>
      </div>
    )
  }

  const failedVideos = (videos || []).filter(v => v.status === 'failed')
  const completedVideos = (videos || []).filter(v => v.status === 'completed')
  const readyVideos = (videos || []).filter(v => v.status === 'completed')

  // Project initials / avatar
  const projectInitials = project?.name
    ? project.name.split(' ').slice(0, 2).map(w => w[0]).join('').toUpperCase()
    : '?'

  return (
    <div className="min-h-screen bg-white flex flex-col">
      <AppHeader />

      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <div className="w-10 h-10 border-[3px] border-gray-900 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
            <p className="text-sm text-gray-500">Loading project...</p>
          </div>
        </div>
      ) : isProcessing ? (
        /* ── PROCESSING STATE: centered pipeline card ── */
        <div className="flex-1 flex items-center justify-center bg-gray-50 p-6">
          <div className="w-full max-w-xl bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
            {/* Card header */}
            <div className="flex items-center gap-4 px-6 pt-6 pb-4 border-b border-gray-100">
              <div className="w-14 h-14 rounded-xl bg-gray-100 flex items-center justify-center text-lg font-bold text-gray-500 flex-shrink-0">
                {projectInitials}
              </div>
              <div>
                <h2 className="font-semibold text-gray-900">{project?.name}</h2>
                {project?.description && (
                  <p className="text-sm text-gray-500">{project.description}</p>
                )}
              </div>
            </div>
            <div className="p-6">
              <ProcessingPipeline
                currentStage={status?.stage || 'initializing'}
                currentStep={status?.current_step || 0}
                totalSteps={status?.total_steps || 3}
                currentVideo={status?.current_video || null}
                errors={status?.errors || []}
                videoStates={status?.video_states || []}
              />
            </div>
            <div className="flex items-center gap-2 px-6 pb-5 text-sm text-gray-500">
              <div className="w-3.5 h-3.5 border-2 border-gray-400 border-t-transparent rounded-full animate-spin" />
              Processing in progress... You can leave this page. We'll notify you when it's ready.
            </div>
          </div>
        </div>
      ) : (
        /* ── DONE STATE: sidebar + main content ── */
        <div className="flex flex-1 overflow-hidden">
          {/* Sidebar */}
          <aside className="w-[280px] flex-shrink-0 border-r border-gray-200 bg-white flex flex-col overflow-y-auto">
            {/* Back link */}
            <div className="px-5 pt-5 mb-4">
              <Link
                href="/projects"
                className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-800 transition-colors"
              >
                <ArrowLeft className="h-4 w-4" />
                Back to Projects
              </Link>
            </div>

            {/* Project info */}
            <div className="px-5 mb-5">
              <div className="w-12 h-12 rounded-xl bg-gray-100 flex items-center justify-center text-base font-bold text-gray-600 mb-3">
                {projectInitials}
              </div>
              <h1 className="font-semibold text-gray-900 text-base leading-snug mb-1">
                {project?.name}
              </h1>
              {project?.description && (
                <p className="text-sm text-gray-500 line-clamp-2 mb-2">{project.description}</p>
              )}
              <div className="flex items-center gap-1.5 text-xs text-gray-400">
                <Calendar className="h-3 w-3" />
                <span>Created {project?.created_at ? formatDate(project.created_at) : '—'}</span>
              </div>
            </div>

            {/* Tab nav */}
            <nav className="px-3 mb-4">
              {SIDEBAR_TABS.map(({ value, label, icon: Icon }) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => setActiveTab(value)}
                  className={cn(
                    'w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium transition-colors mb-0.5',
                    activeTab === value
                      ? 'bg-gray-100 text-gray-900'
                      : 'text-gray-600 hover:bg-gray-50 hover:text-gray-800'
                  )}
                >
                  <div className="flex items-center gap-2.5">
                    <Icon className="h-4 w-4" />
                    {label}
                  </div>
                  {value === 'videos' && (
                    <span className="text-xs bg-gray-200 text-gray-600 rounded-full px-1.5 py-0.5">
                      {(videos || []).length}
                    </span>
                  )}
                </button>
              ))}
            </nav>

            {/* Project actions (edit/delete) */}
            <div className="px-5 mt-auto pb-5 border-t border-gray-100 pt-4 flex items-center gap-2">
              <button
                type="button"
                onClick={handleRetry}
                disabled={retrying || !isFailed}
                title="Retry failed videos"
                className="flex-1 flex items-center justify-center gap-1.5 text-xs text-gray-500 hover:text-gray-800 border border-gray-200 rounded-lg py-2 disabled:opacity-40 transition-colors"
              >
                <RefreshCw className={cn('h-3 w-3', retrying && 'animate-spin')} />
                Retry
              </button>
              <button
                type="button"
                onClick={handleDelete}
                title="Delete project"
                className="flex-1 flex items-center justify-center gap-1.5 text-xs text-red-500 hover:text-red-700 border border-gray-200 hover:border-red-200 rounded-lg py-2 transition-colors"
              >
                <Trash2 className="h-3 w-3" />
                Delete
              </button>
            </div>
          </aside>

          {/* Main content */}
          <main className="flex-1 overflow-auto">
            {/* Error banner */}
            {isFailed && !errorBannerDismissed && (
              <div className="mx-6 mt-5 border border-red-200 bg-red-50 rounded-xl p-4">
                <div className="flex items-start gap-3">
                  <AlertTriangle className="h-4 w-4 text-red-500 flex-shrink-0 mt-0.5" />
                  <div className="flex-1 min-w-0">
                    <h3 className="text-sm font-semibold text-red-700">Processing Failed</h3>
                    <p className="text-sm text-red-600/80 mt-0.5">
                      {failedVideos.length > 0 && completedVideos.length > 0
                        ? `${failedVideos.length} video${failedVideos.length !== 1 ? 's' : ''} failed, ${completedVideos.length} completed. You can review completed content or retry failed videos.`
                        : `All ${failedVideos.length} videos failed to process. Check errors and try again.`}
                    </p>
                    {project?.error_message && (
                      <details className="mt-2">
                        <summary className="text-xs text-red-500 cursor-pointer">Technical details</summary>
                        <pre className="mt-1 text-xs text-red-400 whitespace-pre-wrap break-all bg-red-100 p-2 rounded">
                          {project.error_message}
                        </pre>
                      </details>
                    )}
                    <div className="mt-3">
                      <button
                        type="button"
                        onClick={handleRetry}
                        disabled={retrying}
                        className="inline-flex items-center gap-1.5 text-sm font-medium text-red-700 border border-red-300 rounded-lg px-3 py-1.5 hover:bg-red-100 disabled:opacity-50 transition-colors"
                      >
                        {retrying ? (
                          <><div className="w-3 h-3 border-2 border-red-700 border-t-transparent rounded-full animate-spin" />Retrying...</>
                        ) : (
                          <><RefreshCw className="h-3 w-3" />Retry Failed Videos</>
                        )}
                      </button>
                    </div>
                  </div>
                  <button onClick={() => setErrorBannerDismissed(true)} className="text-red-400 hover:text-red-600 flex-shrink-0">
                    <X className="h-4 w-4" />
                  </button>
                </div>
              </div>
            )}

            {/* Tab content */}
            <motion.div
              key={activeTab}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.15 }}
              className={cn(
                activeTab === 'chat' ? 'h-[calc(100vh-57px)]' : 'p-6',
                'flex flex-col'
              )}
            >
              {activeTab === 'videos' && (
                <>
                  <div className="flex items-center justify-between mb-5">
                    <div>
                      <h2 className="text-xl font-bold text-gray-900">Videos</h2>
                      <p className="text-sm text-gray-500">Manage and monitor your project videos</p>
                    </div>
                    <Link
                      href={`/projects/new`}
                      className="inline-flex items-center gap-1.5 bg-white border border-gray-200 text-sm font-medium text-gray-700 px-3 py-2 rounded-lg hover:bg-gray-50 transition-colors"
                    >
                      <Plus className="h-4 w-4" />
                      Add Videos
                    </Link>
                  </div>
                  <VideoManager projectId={projectId} videos={videos || []} />
                </>
              )}

              {activeTab === 'synthesis' && synthesis && (
                <>
                  <div className="flex items-center justify-between mb-5">
                    <div>
                      <h2 className="text-xl font-bold text-gray-900">Cross-Video Synthesis</h2>
                      <p className="text-sm text-gray-500">
                        Generated {project?.updated_at ? formatDate(project.updated_at) : ''} · {(videos || []).length} sources
                      </p>
                    </div>
                  </div>
                  <ConsolidatedView synthesis={synthesis} />
                </>
              )}
              {activeTab === 'synthesis' && synthesisLoading && (
                <div className="flex items-center justify-center h-64">
                  <div className="w-8 h-8 border-[3px] border-gray-900 border-t-transparent rounded-full animate-spin" />
                </div>
              )}
              {activeTab === 'synthesis' && isDone && !synthesis && !synthesisLoading && (
                <div className="flex items-center justify-center h-64 text-gray-400">
                  <div className="text-center">
                    <FileText className="h-12 w-12 mx-auto mb-3 opacity-20" />
                    <p className="text-sm">No synthesis available yet.</p>
                    <p className="text-xs mt-1 text-gray-400">Synthesis is generated after all videos are processed.</p>
                  </div>
                </div>
              )}

              {activeTab === 'summaries' && (
                <>
                  <div className="mb-5">
                    <h2 className="text-xl font-bold text-gray-900">Video Summaries</h2>
                    <p className="text-sm text-gray-500">Individual AI-generated summaries for each video</p>
                  </div>
                  <VideoSummaryList summaries={summaries || []} isLoading={summariesLoading} />
                </>
              )}

              {activeTab === 'chat' && (
                <ChatContainer
                  messages={messages}
                  videos={videos || []}
                  onSendMessage={(msg, videoIds) => sendMessage(msg, videoIds)}
                  isLoading={isSending}
                />
              )}
            </motion.div>
          </main>
        </div>
      )}
    </div>
  )
}
