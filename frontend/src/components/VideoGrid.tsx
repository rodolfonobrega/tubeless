'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import { Check, Clock, Youtube } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { cn, formatDuration, formatDate, getYouTubeId } from '@/lib/utils'
import type { Video } from '@/types'

interface VideoGridProps {
  videos: Video[]
  selectedVideos: Set<string>
  onToggleSelection: (videoId: string) => void
  onSelectAll?: () => void
  onDeselectAll?: () => void
  isLoading?: boolean
}

export function VideoGrid({
  videos,
  selectedVideos,
  onToggleSelection,
  onSelectAll,
  onDeselectAll,
  isLoading = false,
}: VideoGridProps) {
  const [hoveredVideo, setHoveredVideo] = useState<string | null>(null)

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <VideoCardSkeleton key={i} />
        ))}
      </div>
    )
  }

  const allSelected = videos.length > 0 && selectedVideos.size === videos.length
  const someSelected = selectedVideos.size > 0 && !allSelected

  return (
    <div className="space-y-4">
      {/* Bulk Actions */}
      {(onSelectAll || onDeselectAll) && videos.length > 0 && (
        <div className="flex items-center justify-between p-4 bg-muted/50 rounded-xl">
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={allSelected}
              ref={(input) => {
                if (input) {
                  input.indeterminate = someSelected
                }
              }}
              onChange={() => {
                if (allSelected || someSelected) {
                  onDeselectAll?.()
                } else {
                  onSelectAll?.()
                }
              }}
              className="w-4 h-4 rounded border-input"
            />
            <span className="text-sm text-muted-foreground">
              {selectedVideos.size > 0
                ? `${selectedVideos.size} video${selectedVideos.size > 1 ? 's' : ''} selected`
                : `${videos.length} videos`}
            </span>
          </div>
          {someSelected && (
            <Button variant="ghost" size="sm" onClick={onDeselectAll}>
              Clear selection
            </Button>
          )}
        </div>
      )}

      {/* Video Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {videos.map((video, index) => (
          <motion.div
            key={video.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.05 }}
          >
            <VideoCard
              video={video}
              isSelected={selectedVideos.has(video.id)}
              onToggle={() => onToggleSelection(video.id)}
              isHovered={hoveredVideo === video.id}
              onHoverChange={(isHovered) =>
                setHoveredVideo(isHovered ? video.id : null)
              }
            />
          </motion.div>
        ))}
      </div>

      {videos.length === 0 && (
        <div className="text-center py-12">
          <Youtube className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
          <p className="text-muted-foreground">No videos found</p>
        </div>
      )}
    </div>
  )
}

interface VideoCardProps {
  video: Video
  isSelected: boolean
  onToggle: () => void
  isHovered: boolean
  onHoverChange: (isHovered: boolean) => void
}

function VideoCard({ video, isSelected, onToggle, isHovered, onHoverChange }: VideoCardProps) {
  const youtubeId = getYouTubeId(video.url)

  return (
    <Card
      className={cn(
        'group overflow-hidden transition-all duration-200 cursor-pointer hover:shadow-lg',
        isSelected && 'ring-2 ring-primary'
      )}
      onMouseEnter={() => onHoverChange(true)}
      onMouseLeave={() => onHoverChange(false)}
      onClick={onToggle}
    >
      <div className="relative aspect-video bg-muted">
        {/* Thumbnail */}
        {video.thumbnail_url ? (
          <img
            src={video.thumbnail_url}
            alt={video.title ?? ''}
            className="w-full h-full object-cover"
            loading="lazy"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center bg-muted">
            <Youtube className="h-12 w-12 text-muted-foreground" />
          </div>
        )}

        {/* Duration Badge */}
        {(video.duration ?? 0) > 0 && (
          <Badge
            variant="secondary"
            className="absolute bottom-2 right-2 bg-black/80 text-white border-0"
          >
            <Clock className="h-3 w-3 mr-1" />
            {formatDuration(video.duration ?? 0)}
          </Badge>
        )}

        {/* Selected Overlay */}
        {isSelected && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="absolute inset-0 bg-primary/20 flex items-center justify-center"
          >
            <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center">
              <Check className="h-5 w-5 text-primary-foreground" />
            </div>
          </motion.div>
        )}

        {/* Hover Overlay */}
        {isHovered && !isSelected && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="absolute inset-0 bg-black/40 flex items-center justify-center"
          >
            <div className="w-8 h-8 rounded-full bg-white/90 flex items-center justify-center">
              <Check className="h-5 w-5 text-foreground" />
            </div>
          </motion.div>
        )}

        {/* Transcript Status */}
        {video.status !== 'completed' && (
          <Badge
            variant="destructive"
            className="absolute top-2 left-2"
          >
            No Transcript
          </Badge>
        )}
      </div>

      <CardContent className="p-3">
        <h3 className="font-medium text-sm line-clamp-2 mb-1 group-hover:text-primary transition-colors">
          {video.title}
        </h3>
        <p className="text-xs text-muted-foreground">{video.channel_title}</p>
      </CardContent>
    </Card>
  )
}

function VideoCardSkeleton() {
  return (
    <Card className="overflow-hidden">
      <div className="aspect-video bg-muted animate-pulse" />
      <CardContent className="p-3">
        <div className="h-4 bg-muted rounded mb-2 animate-pulse" />
        <div className="h-3 bg-muted rounded w-3/4 animate-pulse" />
      </CardContent>
    </Card>
  )
}
