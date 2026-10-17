import { Award, ChevronDown, Clock, Flag, Ruler } from 'lucide-react'

import { Badge, RiskBadge } from '@/components/ui'
import { cn } from '@/lib/cn'
import { formatClock, formatDuration, formatMiles } from '@/lib/format'
import type { PlannedRoute } from '@/lib/types'

import { CheckpointList } from './CheckpointList'
import { RiskBar } from './RiskBar'

interface RouteCardProps {
  route: PlannedRoute
  selected: boolean
  onSelect: () => void
}

export function RouteCard({ route, selected, onSelect }: RouteCardProps) {
  const { summary } = route
  return (
    <article
      className={cn(
        'rounded-xl border bg-white transition-shadow',
        selected
          ? 'shadow-panel border-slate-900 ring-1 ring-slate-900'
          : 'border-slate-200 hover:border-slate-300 hover:shadow-sm',
      )}
      aria-current={selected || undefined}
    >
      <button
        type="button"
        onClick={onSelect}
        className="focus-visible:ring-brand-500 flex w-full flex-col gap-3 rounded-xl p-4 text-left focus-visible:ring-2 focus-visible:outline-none"
        aria-expanded={selected}
      >
        <div className="flex items-start justify-between gap-3">
          <div className="flex min-w-0 items-start gap-2.5">
            <span
              className={cn(
                'mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-md text-xs font-bold',
                selected ? 'bg-slate-900 text-white' : 'bg-slate-100 text-slate-700',
              )}
            >
              {route.rank}
            </span>
            <div className="min-w-0">
              <h3 className="truncate text-sm font-semibold text-slate-900">{route.name}</h3>
              <p className="mt-0.5 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-xs text-slate-500">
                <span className="inline-flex items-center gap-1">
                  <Ruler className="h-3 w-3" /> {formatMiles(route.distance_miles)}
                </span>
                <span className="inline-flex items-center gap-1">
                  <Clock className="h-3 w-3" /> {formatDuration(route.duration_seconds)}
                </span>
                <span className="inline-flex items-center gap-1">
                  <Flag className="h-3 w-3" /> arrive {formatClock(route.arrival_time)}
                </span>
              </p>
            </div>
          </div>
          <div className="flex shrink-0 flex-col items-end gap-1">
            {route.recommended && (
              <Badge tone="success">
                <Award className="h-3 w-3" /> Recommended
              </Badge>
            )}
            {!summary.travel_advised && (
              <Badge className={'bg-violet-50 text-violet-700 ring-violet-600/20'}>No travel</Badge>
            )}
          </div>
        </div>

        <RiskBar milesByLevel={summary.miles_by_level} unknownMiles={summary.unknown_miles} />

        <dl className="grid grid-cols-4 gap-2 text-center">
          <Metric
            label="Severe"
            value={`${Math.round(summary.severe_miles)} mi`}
            alert={summary.severe_miles > 0}
          />
          <Metric
            label="High"
            value={`${Math.round(summary.high_miles)} mi`}
            alert={summary.high_miles > 0}
          />
          <Metric label="Avg risk" value={summary.average_risk.toFixed(2)} />
          <div>
            <dt className="text-[10px] font-medium tracking-wide text-slate-500 uppercase">Peak</dt>
            <dd className="mt-0.5 flex justify-center">
              <RiskBadge level={summary.max_level} />
            </dd>
          </div>
        </dl>

        <span className="flex items-center justify-center gap-1 text-[11px] font-medium text-slate-500">
          {selected ? 'Checkpoints' : 'Select route'}
          <ChevronDown className={cn('h-3 w-3 transition-transform', selected && 'rotate-180')} />
        </span>
      </button>

      {selected && (
        <div className="border-t border-slate-100 p-3">
          <CheckpointList route={route} />
        </div>
      )}
    </article>
  )
}

function Metric({ label, value, alert }: { label: string; value: string; alert?: boolean }) {
  return (
    <div>
      <dt className="text-[10px] font-medium tracking-wide text-slate-500 uppercase">{label}</dt>
      <dd
        className={cn(
          'mt-0.5 text-sm font-semibold tabular-nums',
          alert ? 'text-red-600' : 'text-slate-900',
        )}
      >
        {value}
      </dd>
    </div>
  )
}
