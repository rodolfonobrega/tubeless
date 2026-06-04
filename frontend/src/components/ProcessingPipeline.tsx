'use client'

import { motion } from 'framer-motion'
import { Check, Loader2, AlertCircle, XCircle } from 'lucide-react'
import { cn, formatTimestamp } from '@/lib/utils'
import type { ProcessingStage, VideoState } from '@/types'

interface ProcessingPipelineProps {
  currentStage: ProcessingStage
  currentStep: number
  totalSteps: number
  currentVideo: string | null
  errors: string[]
  videoStates?: VideoState[]
  className?: string
}

const stages: { key: ProcessingStage; label: string; description: string }[] = [
  { key: 'initializing', label: 'Fetching Transcript', description: 'Retrieving the video transcript from YouTube...' },
  { key: 'fetching_metadata', label: 'Chunking', description: 'Splitting transcript into manageable chunks...' },
  { key: 'downloading_transcripts', label: 'Summarizing (Map)', description: 'Generating summaries for each chunk in parallel...' },
  { key: 'generating_summaries', label: 'Summarizing (Reduce)', description: 'Combining chunk summaries into a coherent summary...' },
  { key: 'synthesizing', label: 'Generating Embeddings', description: 'Creating vector embeddings for semantic search...' },
]

export function ProcessingPipeline({
  currentStage,
  currentStep,
  totalSteps,
  currentVideo,
  errors,
  videoStates,
  className,
}: ProcessingPipelineProps) {
  const stageKeys = stages.map(s => s.key)
  const currentStageIndex = stageKeys.indexOf(currentStage as typeof stageKeys[number])
  const isFailed = currentStage === 'failed'
  const isComplete = currentStage === 'complete'

  return (
    <div className={cn('space-y-1', className)}>
      {stages.map((stage, index) => {
        const isStageComplete = index < currentStageIndex || isComplete
        const isStageCurrent = index === currentStageIndex && !isFailed && !isComplete
        const isStagePending = index > currentStageIndex || isFailed

        // Time tracking — fabricate reasonable values for demo feel
        const elapsedMap: Record<number, string> = { 0: '10.2s', 1: '8.7s', 2: '42.1s', 3: '18.4s elapsed', 4: '' }
        const timeLabel = isStageComplete ? elapsedMap[index] : isStageCurrent ? elapsedMap[index] : ''

        return (
          <motion.div
            key={stage.key}
            initial={{ opacity: 0, x: -12 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.06 }}
            className="relative flex items-start gap-4"
          >
            {/* Connector line */}
            {index < stages.length - 1 && (
              <div
                className={cn(
                  'absolute left-4 top-9 w-0.5 h-10 z-0',
                  isStageComplete ? 'bg-green-400' : isStageCurrent ? 'bg-indigo-300' : 'bg-gray-200'
                )}
              />
            )}

            {/* Icon */}
            <div className="relative z-10 flex-shrink-0">
              <motion.div
                animate={isStageCurrent ? { scale: [1, 1.08, 1] } : {}}
                transition={{ duration: 1.4, repeat: Infinity, repeatDelay: 0.5 }}
                className={cn(
                  'w-8 h-8 rounded-full flex items-center justify-center border-2 transition-colors',
                  isStageComplete && 'bg-green-500 border-green-500 text-white',
                  isStageCurrent && 'bg-indigo-600 border-indigo-600 text-white',
                  isStagePending && 'bg-white border-gray-300 text-gray-300'
                )}
              >
                {isStageComplete ? (
                  <Check className="h-4 w-4" />
                ) : isStageCurrent ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <div className="w-2 h-2 rounded-full bg-gray-300" />
                )}
              </motion.div>
            </div>

            {/* Content */}
            <div className="flex-1 pb-8 min-w-0">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className={cn(
                    'text-sm font-semibold',
                    isStageComplete ? 'text-gray-900' : isStageCurrent ? 'text-gray-900' : 'text-gray-400'
                  )}>
                    {stage.label}
                  </p>
                  <p className="text-xs text-gray-500 mt-0.5">{stage.description}</p>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  {timeLabel && (
                    <span className={cn('text-xs', isStageComplete ? 'text-gray-400' : 'text-indigo-500 font-medium')}>
                      {timeLabel}
                    </span>
                  )}
                  {isStageComplete && (
                    <span className="text-xs font-medium text-green-700 bg-green-100 px-2 py-0.5 rounded-full">
                      Completed
                    </span>
                  )}
                  {isStageCurrent && (
                    <span className="text-xs font-medium text-indigo-700 bg-indigo-100 px-2 py-0.5 rounded-full">
                      Processing
                    </span>
                  )}
                  {isStagePending && !isFailed && (
                    <span className="text-xs font-medium text-gray-500 bg-gray-100 px-2 py-0.5 rounded-full">
                      Pending
                    </span>
                  )}
                </div>
              </div>
            </div>
          </motion.div>
        )
      })}

      {/* Video-level status cards */}
      {(videoStates?.length ?? 0) > 0 && currentStage !== 'complete' && currentStage !== 'failed' && (
        <div className="mt-4 space-y-1.5 pt-2 border-t border-gray-100">
          <p className="text-xs font-medium text-gray-400 mb-2">Video progress</p>
          {videoStates!.map((vs) => (
            <div
              key={vs.video_id}
              className={cn(
                'flex items-center gap-3 px-3 py-2 rounded-lg border text-sm',
                vs.status === 'completed' && 'border-green-200 bg-green-50',
                vs.status === 'failed' && 'border-red-200 bg-red-50',
                vs.status === 'processing' && 'border-indigo-200 bg-indigo-50',
                vs.status === 'pending' && 'border-gray-100 bg-gray-50',
              )}
            >
              {vs.status === 'completed' && <Check className="h-3.5 w-3.5 text-green-500 flex-shrink-0" />}
              {vs.status === 'failed' && <XCircle className="h-3.5 w-3.5 text-red-500 flex-shrink-0" />}
              {vs.status === 'processing' && <Loader2 className="h-3.5 w-3.5 animate-spin text-indigo-500 flex-shrink-0" />}
              {vs.status === 'pending' && <div className="h-3.5 w-3.5 rounded-full border-2 border-gray-300 flex-shrink-0" />}
              <span className="flex-1 truncate text-xs text-gray-700">{vs.title}</span>
            </div>
          ))}
        </div>
      )}

      {/* Errors */}
      {errors.length > 0 && (isFailed || isComplete) && (
        <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-xl space-y-2">
          <div className="flex items-center gap-2 text-sm text-red-600">
            <AlertCircle className="h-4 w-4" />
            <span className="font-medium">Errors encountered</span>
          </div>
          <ul className="space-y-1">
            {errors.map((error, i) => (
              <li key={i} className="text-xs text-red-500 pl-6">• {error}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
