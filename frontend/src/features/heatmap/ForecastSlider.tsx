import { addHours, format } from 'date-fns'
import { Eye, EyeOff, Pause, Play, SkipBack } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'

import { Button } from '@/components/ui'
import { cn } from '@/lib/cn'
import type { PlannedRoute, TripPlan } from '@/lib/types'

interface ForecastSliderProps {
  plan: TripPlan
  selectedRoute: PlannedRoute | null
  hour: number
  onHourChange: (hour: number) => void
  visible: boolean
  onToggleVisible: () => void
  loading?: boolean
  error?: boolean
}

const PLAY_INTERVAL_MS = 450

export function ForecastSlider({
  plan,
  selectedRoute,
  hour,
  onHourChange,
  visible,
  onToggleVisible,
  loading,
  error,
}: ForecastSliderProps) {
  const [playing, setPlaying] = useState(false)
  const maxHour = plan.forecast_window.hours
  const start = useMemo(() => new Date(plan.forecast_window.start), [plan.forecast_window.start])
  const current = addHours(start, hour)

  useEffect(() => {
    if (!playing) return
    const handle = window.setInterval(() => {
      onHourChange(hour >= maxHour ? 0 : hour + 1)
    }, PLAY_INTERVAL_MS)
    return () => window.clearInterval(handle)
  }, [playing, hour, maxHour, onHourChange])

  // Highlight the span of the selected route's drive on the track.
  const span = useMemo(() => {
    if (!selectedRoute) return null
    const first = selectedRoute.checkpoints[0]
    const last = selectedRoute.checkpoints.at(-1)
    if (!first || !last) return null
    const toHour = (iso: string) =>
      Math.min(maxHour, Math.max(0, (new Date(iso).getTime() - start.getTime()) / 3_600_000))
    return { from: toHour(first.eta), to: toHour(last.eta) }
  }, [selectedRoute, start, maxHour])

  const offsetLabel = hour === 0 ? 'at departure' : `+${hour} h`

  return (
    <div className="shadow-panel pointer-events-auto w-[min(560px,calc(100vw-24px))] rounded-2xl border border-slate-200 bg-white/95 p-3 backdrop-blur">
      <div className="flex items-center gap-2">
        <Button
          size="icon"
          variant="secondary"
          aria-label={playing ? 'Pause forecast playback' : 'Play forecast'}
          onClick={() => setPlaying((p) => !p)}
          disabled={loading || error}
        >
          {playing ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
        </Button>
        <Button
          size="icon"
          variant="ghost"
          aria-label="Back to departure"
          onClick={() => {
            setPlaying(false)
            onHourChange(0)
          }}
          disabled={hour === 0}
        >
          <SkipBack className="h-4 w-4" />
        </Button>
        <div className="min-w-0 flex-1">
          <p className="truncate text-xs font-semibold text-slate-900">
            {format(current, 'EEE MMM d, h:mm a')}{' '}
            <span className="font-normal text-slate-500">· {offsetLabel}</span>
          </p>
          <p className="text-[11px] text-slate-500">
            {error
              ? 'Corridor forecast unavailable.'
              : loading
                ? 'Loading 48 h corridor forecast…'
                : 'Weather risk across the corridor, 0–48 h from departure'}
          </p>
        </div>
        <Button
          size="sm"
          variant="secondary"
          onClick={onToggleVisible}
          aria-pressed={visible}
          leftIcon={visible ? <Eye className="h-3.5 w-3.5" /> : <EyeOff className="h-3.5 w-3.5" />}
        >
          Heatmap
        </Button>
      </div>

      <div className="relative mt-3 px-1">
        {span && (
          <div
            className="bg-brand-500/30 pointer-events-none absolute top-1/2 h-2 -translate-y-1/2 rounded-full"
            style={{
              left: `calc(${(span.from / maxHour) * 100}% )`,
              width: `calc(${((span.to - span.from) / maxHour) * 100}%)`,
            }}
            title="Selected route's driving window"
          />
        )}
        <input
          type="range"
          className={cn('slider relative', (loading || error) && 'opacity-60')}
          min={0}
          max={maxHour}
          step={1}
          value={hour}
          aria-label="Forecast hour"
          aria-valuetext={`${format(current, 'EEE h:mm a')}, ${offsetLabel}`}
          onChange={(event) => {
            setPlaying(false)
            onHourChange(Number(event.target.value))
          }}
        />
        <div className="mt-1 flex justify-between text-[10px] text-slate-400">
          <span>{format(start, 'EEE h a')}</span>
          <span>+12 h</span>
          <span>+24 h</span>
          <span>+36 h</span>
          <span>{format(addHours(start, maxHour), 'EEE h a')}</span>
        </div>
      </div>
    </div>
  )
}
