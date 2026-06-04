'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import { Search, Clock, Youtube } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { formatTimestamp, getYouTubeId } from '@/lib/utils'

export interface TranscriptSegment {
  text: string
  start: number
  duration: number
}

interface TranscriptViewerProps {
  videoId: string
  videoTitle: string
  transcript: TranscriptSegment[]
  videoUrl: string
  className?: string
}

export function TranscriptViewer({
  videoId,
  videoTitle,
  transcript,
  videoUrl,
  className,
}: TranscriptViewerProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const [currentTimestamp, setCurrentTimestamp] = useState<number | null>(null)

  const youtubeId = getYouTubeId(videoUrl)

  // Filter transcript segments based on search
  const filteredSegments = searchQuery
    ? transcript.filter((seg) =>
        seg.text.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : transcript

  // Highlight search matches
  const highlightText = (text: string) => {
    if (!searchQuery) return text

    const regex = new RegExp(`(${searchQuery})`, 'gi')
    const parts = text.split(regex)

    return parts.map((part, i) =>
      regex.test(part) ? (
        <mark key={i} className="bg-yellow-500/30 text-foreground rounded px-0.5">
          {part}
        </mark>
      ) : (
        part
      )
    )
  }

  const handleTimestampClick = (timestamp: number) => {
    setCurrentTimestamp(timestamp)
    // Open video at timestamp
    window.open(
      `https://www.youtube.com/watch?v=${youtubeId}&t=${Math.floor(timestamp)}`,
      '_blank'
    )
  }

  return (
    <div className={cn('flex flex-col h-full', className)}>
      {/* Header */}
      <Card className="flex-shrink-0">
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <Youtube className="h-5 w-5" />
              <span className="line-clamp-1">{videoTitle}</span>
            </CardTitle>
            <Button variant="outline" size="sm" asChild>
              <a
                href={videoUrl}
                target="_blank"
                rel="noopener noreferrer"
              >
                Open Video
              </a>
            </Button>
          </div>
        </CardHeader>
        <CardContent className="pt-0">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search in transcript..."
              className="pl-9"
            />
            {searchQuery && (
              <Button
                variant="ghost"
                size="sm"
                className="absolute right-1 top-1/2 -translate-y-1/2 h-7 px-2"
                onClick={() => setSearchQuery('')}
              >
                Clear
              </Button>
            )}
          </div>
          {searchQuery && (
            <p className="text-xs text-muted-foreground mt-2">
              Found {filteredSegments.length} matching{' '}
              {filteredSegments.length === 1 ? 'segment' : 'segments'}
            </p>
          )}
        </CardContent>
      </Card>

      {/* Transcript */}
      <ScrollArea className="flex-1 mt-4">
        <div className="space-y-1 p-2">
          {filteredSegments.map((segment, index) => (
            <TranscriptSegment
              key={`${segment.start}-${index}`}
              segment={segment}
              index={index}
              onClick={handleTimestampClick}
              isActive={currentTimestamp === segment.start}
              searchQuery={searchQuery}
            />
          ))}

          {filteredSegments.length === 0 && (
            <div className="text-center py-8">
              <Search className="h-8 w-8 mx-auto text-muted-foreground mb-2" />
              <p className="text-sm text-muted-foreground">
                No matches found for "{searchQuery}"
              </p>
            </div>
          )}
        </div>
      </ScrollArea>
    </div>
  )
}

interface TranscriptSegmentProps {
  segment: TranscriptSegment
  index: number
  onClick: (timestamp: number) => void
  isActive: boolean
  searchQuery: string
}

function TranscriptSegment({
  segment,
  index,
  onClick,
  isActive,
  searchQuery,
}: TranscriptSegmentProps) {
  return (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: Math.min(index * 0.01, 0.1) }}
    >
      <button
        onClick={() => onClick(segment.start)}
        className={cn(
          'w-full text-left p-3 rounded-lg transition-all hover:bg-accent group',
          isActive && 'bg-primary/20'
        )}
      >
        <div className="flex items-start gap-3">
          {/* Timestamp Badge */}
          <Badge
            variant="outline"
            className={cn(
              'flex-shrink-0 font-mono text-xs',
              'group-hover:bg-primary group-hover:text-primary-foreground',
              'group-hover:border-primary',
              isActive && 'bg-primary text-primary-foreground border-primary'
            )}
          >
            <Clock className="h-3 w-3 mr-1" />
            {formatTimestamp(segment.start)}
          </Badge>

          {/* Text */}
          <span className="text-sm flex-1 leading-relaxed">
            {searchQuery ? highlightSegmentText(segment.text, searchQuery) : segment.text}
          </span>
        </div>
      </button>
    </motion.div>
  )
}

function highlightSegmentText(text: string, query: string) {
  const regex = new RegExp(`(${query})`, 'gi')
  const parts = text.split(regex)
  return parts.map((part, i) =>
    regex.test(part) ? (
      <mark key={i} className="bg-yellow-500/30 text-foreground rounded px-0.5">
        {part}
      </mark>
    ) : (
      part
    )
  )
}

function cn(...classes: (string | boolean | undefined | null)[]) {
  return classes.filter(Boolean).join(' ')
}
