'use client'

import { FileText, MessageSquare, List, Youtube } from 'lucide-react'
import { useProjectStore } from '@/stores/project-store'
import { cn } from '@/lib/utils'

interface TabNavigationProps {
  className?: string
}

export function TabNavigation({ className }: TabNavigationProps) {
  const { activeTab, setActiveTab } = useProjectStore()

  const tabs = [
    { value: 'videos', label: 'Videos', icon: Youtube },
    { value: 'synthesis', label: 'Synthesis', icon: FileText },
    { value: 'summaries', label: 'Summaries', icon: List },
    { value: 'chat', label: 'Chat', icon: MessageSquare },
  ]

  return (
    <div className={cn('border-b bg-background', className)}>
      <div className="container mx-auto px-4 flex gap-0">
        {tabs.map((tab) => {
          const Icon = tab.icon
          const isActive = activeTab === tab.value
          return (
            <button
              key={tab.value}
              type="button"
              onClick={() => setActiveTab(tab.value)}
              className={cn(
                'relative flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors',
                isActive
                  ? 'border-gray-900 text-gray-900'
                  : 'border-transparent text-gray-500 hover:text-gray-800'
              )}
            >
              <Icon className="h-4 w-4" />
              {tab.label}
            </button>
          )
        })}
      </div>
    </div>
  )
}
