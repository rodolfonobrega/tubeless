'use client'

import { useState, useCallback } from 'react'
import { motion } from 'framer-motion'
import { Search, Sparkles, X } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

interface SearchBarProps {
  onSearch: (query: string) => void
  placeholder?: string
  className?: string
  suggestions?: string[]
  isLoading?: boolean
}

export function SearchBar({
  onSearch,
  placeholder = 'What would you like to learn about today?',
  className,
  suggestions = [],
  isLoading = false,
}: SearchBarProps) {
  const [query, setQuery] = useState('')
  const [showSuggestions, setShowSuggestions] = useState(false)

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault()
      if (query.trim()) {
        onSearch(query.trim())
        setShowSuggestions(false)
      }
    },
    [query, onSearch]
  )

  const handleSuggestionClick = (suggestion: string) => {
    setQuery(suggestion)
    onSearch(suggestion)
    setShowSuggestions(false)
  }

  const filteredSuggestions = suggestions.filter((s) =>
    s.toLowerCase().includes(query.toLowerCase())
  )

  return (
    <div className={cn('w-full max-w-3xl mx-auto', className)}>
      <form onSubmit={handleSubmit} className="relative">
        <motion.div
          initial={{ scale: 0.95, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ duration: 0.3 }}
          className="relative group"
        >
          <div className="absolute inset-0 bg-gradient-to-r from-blue-500/20 to-purple-500/20 rounded-2xl blur-xl opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
          <div className="relative flex items-center bg-card border border-input rounded-2xl shadow-lg overflow-hidden transition-all duration-300 focus-within:ring-2 focus-within:ring-ring focus-within:border-transparent">
            <div className="pl-5 pr-3">
              {isLoading ? (
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                  className="text-muted-foreground"
                >
                  <Sparkles className="h-5 w-5" />
                </motion.div>
              ) : (
                <Search className="h-5 w-5 text-muted-foreground" />
              )}
            </div>
            <Input
              type="text"
              value={query}
              onChange={(e) => {
                setQuery(e.target.value)
                setShowSuggestions(e.target.value.length > 0)
              }}
              onFocus={() => setShowSuggestions(query.length > 0)}
              placeholder={placeholder}
              className="flex-1 border-0 focus-visible:ring-0 focus-visible:shadow-none text-base py-5"
              disabled={isLoading}
            />
            {query && (
              <motion.button
                initial={{ scale: 0, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0, opacity: 0 }}
                type="button"
                onClick={() => setQuery('')}
                className="pr-2 text-muted-foreground hover:text-foreground transition-colors"
              >
                <X className="h-5 w-5" />
              </motion.button>
            )}
            <Button
              type="submit"
              size="lg"
              disabled={!query.trim() || isLoading}
              className="rounded-l-none m-1"
            >
              {isLoading ? 'Searching...' : 'Search'}
            </Button>
          </div>
        </motion.div>

        {/* Suggestions Dropdown */}
        {showSuggestions && filteredSuggestions.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="absolute top-full left-0 right-0 mt-2 bg-card border border-input rounded-xl shadow-lg overflow-hidden z-50"
          >
            {filteredSuggestions.map((suggestion, index) => (
              <button
                key={index}
                type="button"
                onClick={() => handleSuggestionClick(suggestion)}
                className="w-full text-left px-5 py-3 hover:bg-accent transition-colors flex items-center gap-3"
              >
                <Search className="h-4 w-4 text-muted-foreground" />
                <span>{suggestion}</span>
              </button>
            ))}
          </motion.div>
        )}
      </form>

      {/* Example prompts */}
      {!query && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
          className="mt-6 flex flex-wrap gap-2 justify-center"
        >
          {suggestions.slice(0, 4).map((suggestion, index) => (
            <motion.button
              key={index}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.1 * index }}
              type="button"
              onClick={() => handleSuggestionClick(suggestion)}
              className="px-4 py-2 bg-muted/50 hover:bg-muted text-muted-foreground hover:text-foreground rounded-full text-sm transition-all duration-200 hover:scale-105"
            >
              {suggestion}
            </motion.button>
          ))}
        </motion.div>
      )}
    </div>
  )
}
