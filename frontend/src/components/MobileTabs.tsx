import { ListOrdered, Map as MapIcon } from 'lucide-react'

import { cn } from '@/lib/cn'

export type MobileView = 'plan' | 'map'

interface MobileTabsProps {
  view: MobileView
  onChange: (view: MobileView) => void
  routeCount: number
}

/**
 * Bottom tab bar for phones and tablets, where the panel and map can't sit side
 * by side. It is part of the page's flex column (not fixed), so it never covers
 * the map's controls or attribution.
 */
export function MobileTabs({ view, onChange, routeCount }: MobileTabsProps) {
  const tabs: { id: MobileView; label: string; Icon: typeof MapIcon }[] = [
    { id: 'plan', label: routeCount ? `Routes (${routeCount})` : 'Plan', Icon: ListOrdered },
    { id: 'map', label: 'Map', Icon: MapIcon },
  ]
  return (
    <nav
      className="z-30 grid shrink-0 grid-cols-2 border-t border-slate-200 bg-white pb-[env(safe-area-inset-bottom)] lg:hidden"
      aria-label="View"
    >
      {tabs.map(({ id, label, Icon }) => (
        <button
          key={id}
          type="button"
          onClick={() => onChange(id)}
          aria-current={view === id ? 'page' : undefined}
          className={cn(
            'flex h-14 flex-col items-center justify-center gap-0.5 text-[11px] font-medium',
            view === id ? 'text-slate-900' : 'text-slate-500',
          )}
        >
          <Icon className={cn('h-5 w-5', view === id && 'text-brand-600')} aria-hidden />
          {label}
        </button>
      ))}
    </nav>
  )
}
