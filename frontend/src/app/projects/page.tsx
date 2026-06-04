'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import Link from 'next/link'
import { Plus, FolderOpen, Trash2, ChevronRight, Video } from 'lucide-react'
import { AppHeader } from '@/components/AppHeader'
import { useProjects, useDeleteProject } from '@/hooks/use-project'
import { formatDate } from '@/lib/utils'

// Color accents cycling through the reference design palette
const ACCENT_COLORS = [
  'bg-blue-500',
  'bg-green-500',
  'bg-orange-500',
  'bg-purple-500',
  'bg-red-500',
  'bg-yellow-500',
]

export default function ProjectsPage() {
  const { data, isLoading, isError } = useProjects()

  const projects = data?.items || []

  return (
    <div className="min-h-screen bg-white">
      <AppHeader />

      <main className="max-w-screen-xl mx-auto px-6 py-8">
        {/* Page Header */}
        <div className="flex items-center gap-3 mb-1">
          <FolderOpen className="h-5 w-5 text-gray-400" />
          <h1 className="text-2xl font-bold text-gray-900">Projects</h1>
        </div>
        <p className="text-sm text-gray-500 mb-8 ml-8">
          {isLoading ? '…' : `${projects.length} project${projects.length !== 1 ? 's' : ''}`}
        </p>

        {isLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {Array.from({ length: 6 }).map((_, i) => (
              <ProjectCardSkeleton key={i} />
            ))}
          </div>
        ) : isError ? (
          <div className="text-center py-16">
            <p className="text-red-500 font-medium">Failed to load projects</p>
          </div>
        ) : projects.length === 0 ? (
          <EmptyState />
        ) : (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              {projects.map((project, index) => (
                <motion.div
                  key={project.id}
                  initial={{ opacity: 0, y: 16 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.04 }}
                >
                  <ProjectCard project={project} accentColor={ACCENT_COLORS[index % ACCENT_COLORS.length]} />
                </motion.div>
              ))}
            </div>
            <p className="text-sm text-gray-400 mt-6">
              Showing 1–{projects.length} of {projects.length} projects
            </p>
          </>
        )}
      </main>
    </div>
  )
}

interface ProjectCardProps {
  project: {
    id: string
    name: string
    description: string | null
    status: 'pending' | 'processing' | 'fetching' | 'embedding' | 'completed' | 'failed'
    created_at: string
    updated_at: string
    video_count?: number
    processed_count?: number
  }
  accentColor: string
}

function ProjectCard({ project, accentColor }: ProjectCardProps) {
  const [menuOpen, setMenuOpen] = useState(false)
  const deleteProject = useDeleteProject()

  const videoCount = project.video_count ?? 0
  const processedCount = project.processed_count ?? 0
  const progressPct = videoCount > 0 ? Math.round((processedCount / videoCount) * 100) : 0

  return (
    <Link href={`/projects/${project.id}`} className="block">
      <div className="border border-gray-200 rounded-xl bg-white hover:shadow-md transition-shadow duration-150 overflow-hidden group">
        {/* Accent bar */}
        <div className={`h-1 w-full ${accentColor}`} />

        <div className="p-5">
          {/* Title row */}
          <div className="flex items-start justify-between mb-1">
            <h2 className="font-semibold text-gray-900 text-base leading-snug line-clamp-1 flex-1 mr-2">
              {project.name}
            </h2>
            <div className="flex items-center gap-1 flex-shrink-0">
              <ChevronRight className="h-4 w-4 text-gray-400 group-hover:text-gray-600 transition-colors" />
              <button
                onClick={(e) => {
                  e.preventDefault()
                  e.stopPropagation()
                  setMenuOpen(!menuOpen)
                }}
                className="relative ml-1 p-1 rounded hover:bg-gray-100 text-gray-400 hover:text-gray-700 transition-colors"
              >
                {menuOpen && (
                  <>
                    <div className="fixed inset-0 z-10" onClick={(e) => { e.preventDefault(); setMenuOpen(false) }} />
                    <div className="absolute right-0 top-full mt-1 z-20 bg-white border border-gray-200 rounded-lg shadow-md py-1 min-w-[120px]">
                      <button
                        type="button"
                        onClick={async (e) => {
                          e.preventDefault()
                          e.stopPropagation()
                          setMenuOpen(false)
                          if (confirm(`Delete project "${project.name}"?`)) {
                            try {
                              await deleteProject.mutateAsync(project.id)
                            } catch {
                              alert('Failed to delete project')
                            }
                          }
                        }}
                        className="w-full text-left px-3 py-2 text-sm text-red-600 hover:bg-red-50 flex items-center gap-2"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                        Delete
                      </button>
                    </div>
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Description */}
          {project.description && (
            <p className="text-sm text-gray-500 line-clamp-1 mb-3">{project.description}</p>
          )}

          {/* Thumbnail stack area */}
          <div className="flex items-center justify-between mb-4 mt-2">
            <div className="relative w-28 h-16 flex-shrink-0">
              {/* Back card */}
              <div className="absolute top-0 right-1 w-[84px] h-[52px] rounded-lg bg-gray-100 border border-gray-200/80 shadow-sm opacity-60 transform translate-x-3 -translate-y-1.5 rotate-[6deg]" />
              {/* Middle card */}
              <div className="absolute top-1 right-2 w-[84px] h-[52px] rounded-lg bg-gray-100 border border-gray-200/90 shadow-sm opacity-80 transform translate-x-1.5 -translate-y-1 rotate-[3deg]" />
              {/* Front card */}
              <div className="absolute bottom-0 left-0 w-24 h-[56px] rounded-lg bg-gray-50 border border-gray-200 shadow flex items-center justify-center text-gray-400 group-hover:text-red-500 transition-colors">
                <Video className="h-5 w-5 transition-transform group-hover:scale-110 duration-200" />
              </div>
            </div>
            <div className="text-sm text-gray-500 font-medium flex items-center gap-1.5 pr-2">
              <span className="bg-gray-100 px-2.5 py-1 rounded-full text-xs text-gray-700 flex items-center gap-1 border border-gray-200">
                <Video className="h-3 w-3" />
                {videoCount} video{videoCount !== 1 ? 's' : ''}
              </span>
            </div>
          </div>

          {/* Progress */}
          <div className="space-y-1">
            <div className="flex items-center justify-between text-xs text-gray-500">
              <span>{processedCount} of {videoCount} videos processed</span>
              <span className="font-medium">{progressPct}%</span>
            </div>
            <div className="h-1 bg-gray-100 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all ${accentColor}`}
                style={{ width: `${progressPct}%` }}
              />
            </div>
          </div>
        </div>
      </div>
    </Link>
  )
}

function EmptyState() {
  return (
    <div className="text-center py-20">
      <FolderOpen className="h-16 w-16 mx-auto text-gray-200 mb-4" />
      <h3 className="text-lg font-semibold text-gray-900 mb-1">No projects yet</h3>
      <p className="text-sm text-gray-500 mb-6">Create your first project to start synthesizing knowledge from YouTube</p>
      <Link
        href="/projects/new"
        className="inline-flex items-center gap-2 bg-gray-900 text-white text-sm font-medium px-5 py-2.5 rounded-md hover:bg-gray-700 transition-colors"
      >
        <Plus className="h-4 w-4" />
        Create Project
      </Link>
    </div>
  )
}

function ProjectCardSkeleton() {
  return (
    <div className="border border-gray-200 rounded-xl overflow-hidden animate-pulse">
      <div className="h-1 bg-gray-200" />
      <div className="p-5 space-y-3">
        <div className="h-5 bg-gray-100 rounded w-3/4" />
        <div className="h-4 bg-gray-100 rounded w-full" />
        <div className="h-16 bg-gray-100 rounded" />
        <div className="h-2 bg-gray-100 rounded w-full" />
      </div>
    </div>
  )
}
