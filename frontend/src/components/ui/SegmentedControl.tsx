import { cn } from '@/lib/cn'

interface Option<T extends string | number> {
  value: T
  label: string
}

interface SegmentedControlProps<T extends string | number> {
  value: T
  onChange: (value: T) => void
  options: Option<T>[]
  ariaLabel: string
  className?: string
}

export function SegmentedControl<T extends string | number>({
  value,
  onChange,
  options,
  ariaLabel,
  className,
}: SegmentedControlProps<T>) {
  return (
    <div
      role="radiogroup"
      aria-label={ariaLabel}
      className={cn('grid gap-1 rounded-lg bg-slate-100 p-1', className)}
      style={{ gridTemplateColumns: `repeat(${options.length}, minmax(0, 1fr))` }}
    >
      {options.map((option) => {
        const active = option.value === value
        return (
          <button
            key={String(option.value)}
            type="button"
            role="radio"
            aria-checked={active}
            onClick={() => onChange(option.value)}
            className={cn(
              'focus-visible:ring-brand-500 h-8 rounded-md text-xs font-medium transition-colors focus-visible:ring-2 focus-visible:outline-none',
              active ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-600 hover:text-slate-900',
            )}
          >
            {option.label}
          </button>
        )
      })}
    </div>
  )
}
