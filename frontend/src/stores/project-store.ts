import { create } from 'zustand'
import { devtools } from 'zustand/middleware'
import type { Project, Video, ProcessingStatus } from '@/types'

interface SelectedVideo {
  videoId: string
  checked: boolean
}

interface ProjectState {
  // Current project
  currentProject: Project | null
  videos: Video[]
  selectedVideos: Set<string>
  processingStatus: ProcessingStatus | null

  // UI state
  activeTab: string
  sidebarOpen: boolean

  // Actions
  setCurrentProject: (project: Project | null) => void
  setVideos: (videos: Video[]) => void
  setProcessingStatus: (status: ProcessingStatus | null) => void
  toggleVideoSelection: (videoId: string) => void
  selectAllVideos: () => void
  deselectAllVideos: () => void
  setActiveTab: (tab: string) => void
  setSidebarOpen: (open: boolean) => void
  reset: () => void
}

const initialState = {
  currentProject: null,
  videos: [],
  selectedVideos: new Set<string>(),
  processingStatus: null,
  activeTab: 'videos',
  sidebarOpen: true,
}

export const useProjectStore = create<ProjectState>()(
  devtools(
    (set) => ({
      ...initialState,

      setCurrentProject: (project) =>
        set({ currentProject: project, selectedVideos: new Set<string>() }),

      setVideos: (videos) => set({ videos }),

      setProcessingStatus: (status) => set({ processingStatus: status }),

      toggleVideoSelection: (videoId) =>
        set((state) => {
          const newSelected = new Set(state.selectedVideos)
          if (newSelected.has(videoId)) {
            newSelected.delete(videoId)
          } else {
            newSelected.add(videoId)
          }
          return { selectedVideos: newSelected }
        }),

      selectAllVideos: () =>
        set((state) => ({
          selectedVideos: new Set(state.videos.map((v) => v.id)),
        })),

      deselectAllVideos: () => set({ selectedVideos: new Set<string>() }),

      setActiveTab: (tab) => set({ activeTab: tab }),

      setSidebarOpen: (open) => set({ sidebarOpen: open }),

      reset: () => set(initialState),
    }),
    { name: 'ProjectStore' }
  )
)
