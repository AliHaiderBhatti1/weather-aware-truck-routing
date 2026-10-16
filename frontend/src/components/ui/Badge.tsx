import type { ReactNode } from 'react'

import { cn } from '@/lib/cn'
import { RISK_META, type RiskLevel } from '@/lib/risk'

interface BadgeProps {
  children: ReactNode
  className?: string
  tone?: 'neutral' | 'brand' | 'success'
}

const tones = {
  neutral: 'bg-slate-100 text-slate-700 ring-slate-500/10',
  brand: 'bg-brand-50 text-brand-700 ring-brand-500/20',
  success: 'bg-emerald-50 text-emerald-700 ring-emerald-600/20',
}

export function Badge({ children, className, tone = 'neutral' }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-[11px] font-semibold ring-1 ring-inset',
        tones[tone],
        className,
      )}
    >
      {children}
    </span>
  )
}

export function RiskBadge({ level, className }: { level: RiskLevel | null; className?: string }) {
  if (!level) {
    return (
      <Badge className={className} tone="neutral">
        No data
      </Badge>
    )
  }
  const meta = RISK_META[level]
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-md px-2 py-0.5 text-[11px] font-semibold ring-1 ring-inset',
        meta.badge,
        className,
      )}
    >
      <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: meta.color }} />
      {meta.label}
    </span>
  )
}
