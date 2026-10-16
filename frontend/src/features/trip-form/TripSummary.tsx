import { ArrowRight, CalendarClock, Pencil, RotateCcw, Weight } from 'lucide-react'

import { Button } from '@/components/ui'
import { formatDayTime, formatPounds } from '@/lib/format'
import type { TripPlan } from '@/lib/types'

interface TripSummaryProps {
  plan: TripPlan
  onEdit: () => void
  onReset: () => void
}

export function TripSummary({ plan, onEdit, onReset }: TripSummaryProps) {
  const { origin, destination, departure_time, load_weight_lb, checkpoint_interval_miles } =
    plan.request
  return (
    <div className="flex items-start justify-between gap-3 rounded-xl border border-slate-200 bg-white p-4">
      <div className="min-w-0 text-sm">
        <p className="flex items-center gap-1.5 font-semibold text-slate-900">
          <span className="truncate">{origin.name}</span>
          <ArrowRight className="h-3.5 w-3.5 shrink-0 text-slate-400" />
          <span className="truncate">{destination.name}</span>
        </p>
        <p className="mt-1 flex flex-wrap gap-x-3 gap-y-0.5 text-xs text-slate-500">
          <span className="inline-flex items-center gap-1">
            <CalendarClock className="h-3 w-3" /> {formatDayTime(departure_time)}
          </span>
          <span className="inline-flex items-center gap-1">
            <Weight className="h-3 w-3" /> {formatPounds(load_weight_lb)}
          </span>
          <span>every {checkpoint_interval_miles} mi</span>
        </p>
      </div>
      <div className="flex shrink-0 flex-col gap-1.5 sm:flex-row">
        <Button
          variant="secondary"
          size="sm"
          onClick={onEdit}
          leftIcon={<Pencil className="h-3 w-3" />}
        >
          Edit
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={onReset}
          leftIcon={<RotateCcw className="h-3 w-3" />}
          title="Clear this plan and start over"
        >
          New trip
        </Button>
      </div>
    </div>
  )
}
