import { AlertTriangle, CircleAlert, Info } from 'lucide-react'
import type { ReactNode } from 'react'

import { cn } from '@/lib/cn'

type Tone = 'info' | 'warning' | 'error'

const styles: Record<Tone, { box: string; Icon: typeof Info }> = {
  info: { box: 'border-sky-200 bg-sky-50 text-sky-900', Icon: Info },
  warning: { box: 'border-amber-200 bg-amber-50 text-amber-900', Icon: AlertTriangle },
  error: { box: 'border-red-200 bg-red-50 text-red-900', Icon: CircleAlert },
}

export function Alert({
  tone = 'info',
  title,
  children,
  className,
}: {
  tone?: Tone
  title?: string
  children?: ReactNode
  className?: string
}) {
  const { box, Icon } = styles[tone]
  return (
    <div
      role={tone === 'error' ? 'alert' : 'status'}
      className={cn('flex gap-2.5 rounded-lg border p-3 text-sm', box, className)}
    >
      <Icon className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
      <div className="min-w-0 flex-1">
        {title && <p className="font-semibold">{title}</p>}
        {children && (
          <div className={cn(title && 'mt-0.5', 'text-[13px] leading-snug')}>{children}</div>
        )}
      </div>
    </div>
  )
}
