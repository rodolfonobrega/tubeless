'use client'

import Link from 'next/link'
import Image from 'next/image'
import { usePathname } from 'next/navigation'
import { FolderOpen, Search, Settings, Plus } from 'lucide-react'

const navLinks = [
  { href: '/projects', label: 'Projects', icon: FolderOpen },
  { href: '/projects/new', label: 'Search', icon: Search },
  { href: '/settings', label: 'Settings', icon: Settings },
]

export function AppHeader() {
  const pathname = usePathname()

  return (
    <header className="sticky top-0 z-50 bg-white border-b border-gray-200">
      <div className="max-w-screen-xl mx-auto px-6 h-14 flex items-center justify-between">
        {/* Logo */}
        <Link href="/projects" className="flex items-center gap-2">
          <Image
            src="/assets/tubeless-icon.svg"
            alt="TubeLess icon"
            width={50}
            height={50}
            className="h-6 w-6"
          />
          <span className="text-xl font-bold tracking-tight select-none">
            Tube<span className="text-red-600">Less</span>
          </span>
        </Link>

        {/* Nav */}
        <nav className="flex items-center gap-1">
          {navLinks.map(({ href, label, icon: Icon }) => {
            const isActive = pathname === href || (href !== '/projects/new' && pathname.startsWith(href) && href !== '/projects/new')
            return (
              <Link
                key={href}
                href={href}
                className={`inline-flex items-center gap-1.5 px-3 py-2 rounded-md text-sm font-medium transition-colors
                  ${isActive
                    ? 'text-gray-900 border-b-2 border-gray-900 rounded-b-none pb-[6px]'
                    : 'text-gray-500 hover:text-gray-800 hover:bg-gray-50'
                  }`}
              >
                <Icon className="h-4 w-4" />
                {label}
              </Link>
            )
          })}
        </nav>

        {/* CTA */}
        <Link
          href="/projects/new"
          className="inline-flex items-center gap-1.5 bg-gray-900 text-white text-sm font-medium px-4 py-2 rounded-md hover:bg-gray-700 transition-colors"
        >
          <Plus className="h-4 w-4" />
          New Project
        </Link>
      </div>
    </header>
  )
}
