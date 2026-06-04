import axios, { AxiosError } from 'axios'
import type {
  Project,
  Video,
  ConsolidatedSynthesis,
  IndividualSummary,
  ChatRequest,
  ChatResponse,
  CreateProjectRequest,
  ProcessingStatus,
} from '@/types'

const API_BASE_URL = '/api/v1'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

api.interceptors.response.use(
  (response) => response,
  (error: AxiosError<{ message: string; detail?: string }>) => {
    const message = error.response?.data?.message || error.response?.data?.detail || error.message
    return Promise.reject(new Error(message))
  }
)

// Projects API
export const projectsApi = {
  create: async (data: CreateProjectRequest): Promise<Project> => {
    const response = await api.post<Project>('/projects', data)
    return response.data
  },

  list: async (offset = 0, limit = 20): Promise<{ items: Project[]; total: number }> => {
    const response = await api.get<{ projects: Project[]; total: number }>('/projects', {
      params: { offset, limit },
    })
    return {
      items: response.data.projects,
      total: response.data.total,
    }
  },

  get: async (id: string): Promise<Project> => {
    const response = await api.get<Project>(`/projects/${id}`)
    return response.data
  },

  delete: async (id: string): Promise<void> => {
    await api.delete(`/projects/${id}`)
  },

  getStatus: async (id: string): Promise<ProcessingStatus> => {
    const response = await api.get<ProcessingStatus>(`/projects/${id}/status`)
    return response.data
  },

  getVideos: async (id: string): Promise<Video[]> => {
    const response = await api.get<{ videos: Video[]; total: number }>(`/projects/${id}/videos`)
    return response.data.videos
  },

  retryVideo: async (projectId: string, videoId: string): Promise<Video> => {
    const response = await api.post<Video>(`/projects/${projectId}/videos/${videoId}/retry`)
    return response.data
  },

  retryAll: async (projectId: string): Promise<Project> => {
    const response = await api.post<Project>(`/projects/${projectId}/retry`)
    return response.data
  },
}

// Synthesis API
export const synthesisApi = {
  getConsolidated: async (projectId: string): Promise<ConsolidatedSynthesis> => {
    const response = await api.get<ConsolidatedSynthesis>(
      `/projects/${projectId}/synthesis/consolidated`
    )
    return response.data
  },

  getSummaries: async (projectId: string): Promise<IndividualSummary[]> => {
    const response = await api.get<IndividualSummary[]>(
      `/projects/${projectId}/synthesis/summaries`
    )
    return response.data
  },

  regenerate: async (projectId: string): Promise<ConsolidatedSynthesis> => {
    const response = await api.post<ConsolidatedSynthesis>(
      `/projects/${projectId}/synthesis/regenerate`
    )
    return response.data
  },
}

// Chat API
export const chatApi = {
  streamMessage: async (
    data: ChatRequest,
    onChunk: (chunk: string) => void,
    onComplete: (sources: ChatResponse['sources']) => void,
    onError: (error: Error) => void
  ): Promise<void> => {
    try {
      const response = await fetch(`${API_BASE_URL}/chat/projects/${data.project_id}/send`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message: data.message, video_ids: data.video_ids }),
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const reader = response.body?.getReader()
      const decoder = new TextDecoder()

      if (!reader) {
        throw new Error('No reader available')
      }

      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const payload = line.slice(6)
            if (payload === '[DONE]') continue
            try {
              const parsed = JSON.parse(payload)
              if (parsed.content) onChunk(parsed.content)
              if (parsed.sources?.length > 0) onComplete(parsed.sources)
            } catch {
              // Ignore parse errors for partial chunks
            }
          }
        }
      }
    } catch (error) {
      onError(error as Error)
    }
  },
}

// Videos API
export const videosApi = {
  getTranscript: async (videoId: string): Promise<unknown> => {
    const response = await api.get<unknown>(`/videos/${videoId}/transcript`)
    return response.data
  },
}

// Search API
export interface YouTubeSearchResult {
  id: string
  title: string
  thumbnail_url: string
  channel: string
  duration_seconds: number
  published_at?: string
  relevance_score?: number
  pre_selected?: boolean
}

export const searchApi = {
  searchVideos: async (
    query: string,
    mode: 'smart' | 'direct' = 'smart',
    offset = 0,
    limit = 20,
  ): Promise<{
    videos: YouTubeSearchResult[]
    total: number
    offset: number
    limit: number
    search_terms: string[]
  }> => {
    const response = await api.post<{
      videos: YouTubeSearchResult[]
      total: number
      offset: number
      limit: number
      search_terms: string[]
    }>(`/search/smart?q=${encodeURIComponent(query)}&mode=${mode}&offset=${offset}&limit=${limit}`)
    return response.data
  },
}

export const settingsApi = {
  get: (): Promise<{ settings: Record<string, unknown>; defaults: Record<string, unknown> }> =>
    api.get('/settings').then((r) => r.data),
  update: (settings: Record<string, unknown>): Promise<{ settings: Record<string, unknown>; defaults: Record<string, unknown> }> =>
    api.put('/settings', { settings }).then((r) => r.data),
}

export default api
