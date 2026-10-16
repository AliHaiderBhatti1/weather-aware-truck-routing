import type { ReactNode } from 'react'

import { cn } from '@/lib/cn'

interface FieldProps {
  label: string
  htmlFor?: string
  hint?: string
  error?: string
  className?: string
  children: ReactNode
}

export function Field({ label, htmlFor, hint, error, className, children }: FieldProps) {
  return (
    <div className={cn('flex flex-col gap-1.5', className)}>
      <label htmlFor={htmlFor} className="text-xs font-semibold tracking-wide text-slate-600">
        {label}
      </label>
      {children}
      {error ? (
        <p className="text-xs text-red-600" role="alert">
          {error}
        </p>
      ) : hint ? (
        <p className="text-xs text-slate-500">{hint}</p>
      ) : null}
    </div>
  )
}

export const inputClassName =
  'h-10 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-900 shadow-xs placeholder:text-slate-400 focus:border-brand-500 focus:ring-2 focus:ring-brand-500/30 focus:outline-none disabled:bg-slate-50 aria-[invalid=true]:border-red-400'
