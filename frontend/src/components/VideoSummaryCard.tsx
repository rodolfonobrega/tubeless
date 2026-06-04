'use client'

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ChevronDown, ChevronUp, Youtube, Clock, Calendar } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { cn, formatDuration, formatDate, getYouTubeId } from '@/lib/utils'
import type { IndividualSummary } from '@/types'

interface VideoSummaryCardProps {
  summary: IndividualSummary
  index: number
}

export function VideoSummaryCard({ summary, index }: VideoSummaryCardProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const youtubeId = getYouTubeId(summary.url)

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05 }}
    >
      <Card className="overflow-hidden">
        <CardHeader
          className={cn(
            'cursor-pointer transition-colors hover:bg-muted/50',
            isExpanded && 'bg-muted/50'
          )}
          onClick={() => setIsExpanded(!isExpanded)}
        >
          <div className="flex items-start gap-4">
            {/* Thumbnail */}
            <div className="relative flex-shrink-0 w-32 aspect-video rounded-lg overflow-hidden bg-muted">
              {summary.thumbnail_url ? (
                <img
                  src={summary.thumbnail_url}
                  alt={summary.title}
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center">
                  <Youtube className="h-8 w-8 text-muted-foreground" />
                </div>
              )}
            </div>

            {/* Content */}
            <div className="flex-1 min-w-0">
              <CardTitle className="text-base line-clamp-2 mb-1">
                {summary.title}
              </CardTitle>
              <div className="flex items-center gap-3 text-xs text-muted-foreground">
                <a
                  href={summary.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-primary transition-colors"
                  onClick={(e) => e.stopPropagation()}
                >
                  YouTube
                </a>
                <span>•</span>
                <span>{formatDate(summary.created_at)}</span>
              </div>
            </div>

            {/* Expand Button */}
            <Button variant="ghost" size="icon" className="flex-shrink-0">
              {isExpanded ? (
                <ChevronUp className="h-4 w-4" />
              ) : (
                <ChevronDown className="h-4 w-4" />
              )}
            </Button>
          </div>
        </CardHeader>

        <AnimatePresence>
          {isExpanded && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
            >
              <CardContent className="pt-0 space-y-4">
                {/* Summary */}
                <div>
                  <h4 className="text-sm font-medium mb-2">Summary</h4>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    {summary.summary}
                  </p>
                </div>

                {/* Key Points */}
                {summary.key_points.length > 0 && (
                  <div>
                    <h4 className="text-sm font-medium mb-2">Key Points</h4>
                    <ul className="space-y-2">
                      {summary.key_points.map((point, idx) => (
                        <li
                          key={idx}
                          className="text-sm text-muted-foreground flex gap-2"
                        >
                          <span className="text-primary flex-shrink-0">•</span>
                          <span>{point}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </CardContent>
            </motion.div>
          )}
        </AnimatePresence>
      </Card>
    </motion.div>
  )
}

interface VideoSummaryListProps {
  summaries: IndividualSummary[]
  isLoading?: boolean
}

export function VideoSummaryList({
  summaries,
  isLoading = false,
}: VideoSummaryListProps) {
  if (isLoading) {
    return (
      <div className="space-y-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <VideoSummaryCardSkeleton key={i} />
        ))}
      </div>
    )
  }

  if (summaries.length === 0) {
    return (
      <div className="text-center py-12">
        <Youtube className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
        <p className="text-muted-foreground">No summaries available yet</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {summaries.map((summary, index) => (
        <VideoSummaryCard key={summary.id} summary={summary} index={index} />
      ))}
    </div>
  )
}

function VideoSummaryCardSkeleton() {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-start gap-4">
          <div className="flex-shrink-0 w-32 aspect-video rounded-lg bg-muted animate-pulse" />
          <div className="flex-1 space-y-2">
            <div className="h-5 bg-muted rounded animate-pulse w-3/4" />
            <div className="h-4 bg-muted rounded animate-pulse w-1/2" />
          </div>
        </div>
      </CardHeader>
    </Card>
  )
}
