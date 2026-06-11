'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import { Clock, ExternalLink } from 'lucide-react'
import { formatTimestamp, getVideoDisplayTitle, getYouTubeId } from '@/lib/utils'
import type { ConsolidatedSynthesis } from '@/types'

interface ConsolidatedViewProps {
  synthesis: ConsolidatedSynthesis
  className?: string
}

// Sections for the sources panel (groups content by section number)
const SECTION_LABELS: Record<number, string> = {
  0: 'Overview',
  1: 'Main Takeaways',
  2: 'Key Concepts',
  3: 'Full Summary',
  4: 'Notable Quotes',
}

export function ConsolidatedView({ synthesis, className }: ConsolidatedViewProps) {
  const [expandedSources, setExpandedSources] = useState<number[]>([0])

  const toggleSection = (idx: number) => {
    setExpandedSources((prev) =>
      prev.includes(idx) ? prev.filter((i) => i !== idx) : [...prev, idx]
    )
  }

  // Flatten notable quotes into a structure for the sources panel
  const quoteSources = synthesis.notable_quotes.map((q) => ({
    thumbnail: `https://img.youtube.com/vi/${getYouTubeId(q.video_id)}/mqdefault.jpg`,
    title: getVideoDisplayTitle(q.video_title, q.video_id),
    timestamp: formatTimestamp(q.timestamp),
    youtubeId: getYouTubeId(q.video_id),
    timestampSec: q.timestamp,
  }))

  return (
    <div className="flex gap-0 h-full">
      {/* Main content - 70% */}
      <div className="flex-1 overflow-y-auto px-6 py-2 space-y-8 min-w-0">
        {/* Overview */}
        <section>
          <h2 className="text-lg font-bold text-gray-900 mb-2">1. Overview</h2>
          <p className="text-sm text-gray-700 leading-relaxed">
            {synthesis.speaker_perspective}
          </p>
        </section>

        {/* Main Takeaways */}
        {synthesis.main_takeaways.length > 0 && (
          <section>
            <h2 className="text-lg font-bold text-gray-900 mb-3">2. Main Takeaways</h2>
            <ol className="space-y-2">
              {synthesis.main_takeaways.map((takeaway, i) => (
                <motion.li
                  key={i}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className="flex items-start gap-3"
                >
                  <span className="flex-shrink-0 text-sm font-semibold text-gray-400 w-5 mt-0.5">
                    {i + 1}.
                  </span>
                  <p className="text-sm text-gray-700 leading-relaxed">{takeaway}</p>
                </motion.li>
              ))}
            </ol>
          </section>
        )}

        {/* Key Concepts */}
        {synthesis.key_concepts.length > 0 && (
          <section>
            <h2 className="text-lg font-bold text-gray-900 mb-3">3. Key Concepts</h2>
            <div className="flex flex-wrap gap-2">
              {synthesis.key_concepts.map((concept, i) => (
                <span key={i} className="text-sm px-3 py-1 rounded-full bg-gray-100 text-gray-700 font-medium">
                  {concept}
                </span>
              ))}
            </div>
          </section>
        )}

        {/* Notable Quotes */}
        {synthesis.notable_quotes.length > 0 && (
          <section>
            <h2 className="text-lg font-bold text-gray-900 mb-3">4. Notable Quotes</h2>
            <div className="space-y-4">
              {synthesis.notable_quotes.map((quote, i) => (
                <div key={i} className="pl-4 border-l-2 border-gray-200">
                  <p className="text-sm italic text-gray-700 mb-1">"{quote.text}"</p>
                  {quote.context && (
                    <p className="text-xs text-gray-500 mb-1">{quote.context}</p>
                  )}
                  <a
                    href={`https://www.youtube.com/watch?v=${getYouTubeId(quote.video_id)}&t=${quote.timestamp}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-xs text-indigo-600 hover:underline"
                  >
                    <Clock className="h-3 w-3" />
                    {formatTimestamp(quote.timestamp)}
                    <ExternalLink className="h-3 w-3" />
                    <span className="text-gray-500">- {getVideoDisplayTitle(quote.video_title, quote.video_id)}</span>
                  </a>
                </div>
              ))}
            </div>
          </section>
        )}
      </div>

      {/* Sources panel - 30% */}
      <aside className="w-72 flex-shrink-0 border-l border-gray-200 overflow-y-auto bg-white">
        <div className="sticky top-0 bg-white border-b border-gray-100 px-5 py-4">
          <h3 className="text-sm font-semibold text-gray-900">Sources</h3>
          <p className="text-xs text-gray-500 mt-0.5">Sources that contributed to this section</p>
        </div>

        <div className="px-5 py-4 space-y-5">
          {/* For each section, show contributing quotes/sources */}
          {synthesis.notable_quotes.length > 0 && (
            <div>
              <button
                type="button"
                onClick={() => toggleSection(0)}
                className="w-full flex items-center justify-between text-sm font-semibold text-gray-900 mb-2"
              >
                <span>{SECTION_LABELS[4]}</span>
                <span className="text-xs text-gray-400">{quoteSources.length} sources</span>
              </button>
              {expandedSources.includes(0) && (
                <div className="space-y-2">
                  {quoteSources.map((src, i) => (
                    <a
                      key={i}
                      href={`https://www.youtube.com/watch?v=${src.youtubeId}&t=${src.timestampSec}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-2.5 p-2 rounded-lg hover:bg-gray-50 transition-colors group"
                    >
                      <div className="w-16 h-10 rounded-md overflow-hidden flex-shrink-0 bg-gray-100">
                        <img src={src.thumbnail} alt={src.title} className="w-full h-full object-cover" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-medium text-gray-800 line-clamp-2 leading-snug">{src.title}</p>
                        <p className="text-xs text-gray-500 mt-0.5">{src.timestamp}</p>
                      </div>
                      <ExternalLink className="h-3 w-3 text-gray-300 group-hover:text-gray-500 flex-shrink-0" />
                    </a>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Key concepts section */}
          {synthesis.key_concepts.length > 0 && (
            <div>
              <button
                type="button"
                onClick={() => toggleSection(1)}
                className="w-full flex items-center justify-between text-sm font-semibold text-gray-900 mb-2"
              >
                <span>Key Concepts</span>
                <span className="text-xs text-gray-400">{synthesis.key_concepts.length} concepts</span>
              </button>
              {expandedSources.includes(1) && (
                <div className="flex flex-wrap gap-1.5">
                  {synthesis.key_concepts.map((c, i) => (
                    <span key={i} className="text-xs px-2 py-1 rounded-full bg-indigo-50 text-indigo-700">{c}</span>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Main takeaways section */}
          {synthesis.main_takeaways.length > 0 && (
            <div>
              <button
                type="button"
                onClick={() => toggleSection(2)}
                className="w-full flex items-center justify-between text-sm font-semibold text-gray-900 mb-2"
              >
                <span>Main Takeaways</span>
                <span className="text-xs text-gray-400">{synthesis.main_takeaways.length} points</span>
              </button>
              {expandedSources.includes(2) && (
                <ol className="space-y-1.5">
                  {synthesis.main_takeaways.map((t, i) => (
                    <li key={i} className="text-xs text-gray-600 flex items-start gap-1.5">
                      <span className="font-semibold text-gray-400">{i + 1}.</span>
                      <span>{t}</span>
                    </li>
                  ))}
                </ol>
              )}
            </div>
          )}
        </div>
      </aside>
    </div>
  )
}
