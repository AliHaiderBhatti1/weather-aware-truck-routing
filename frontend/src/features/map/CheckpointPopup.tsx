import { CloudRain, Snowflake, Thermometer, Wind } from 'lucide-react'
import { Popup } from 'react-map-gl/maplibre'

import { RiskBadge } from '@/components/ui'
import { formatDayTime, formatInchesPerHour, formatMiles } from '@/lib/format'
import type { Checkpoint, PlannedRoute } from '@/lib/types'
import { weatherCodeLabel } from '@/lib/weatherCodes'

interface CheckpointPopupProps {
  route: PlannedRoute
  checkpoint: Checkpoint
}

export function CheckpointPopup({ route, checkpoint }: CheckpointPopupProps) {
  const { weather, risk } = checkpoint
  const isLast = checkpoint.index === route.checkpoints.length - 1
  const title =
    checkpoint.index === 0 ? 'Departure' : isLast ? 'Arrival' : `Checkpoint ${checkpoint.index}`

  return (
    <Popup
      longitude={checkpoint.lon}
      latitude={checkpoint.lat}
      anchor="bottom"
      offset={12}
      closeButton={false}
      closeOnClick={false}
      maxWidth="280px"
    >
      <div className="w-64 p-3 text-slate-800">
        <div className="flex items-start justify-between gap-2">
          <div>
            <p className="text-xs font-semibold text-slate-500">{title}</p>
            <p className="text-sm font-semibold">{formatDayTime(checkpoint.eta)}</p>
            <p className="text-xs text-slate-500">
              {formatMiles(checkpoint.distance_from_start_miles)} from start · {route.name}
            </p>
          </div>
          <RiskBadge level={risk?.level ?? null} />
        </div>

        {weather ? (
          <dl className="mt-3 grid grid-cols-2 gap-x-3 gap-y-1.5 text-xs">
            <Stat
              icon={<Wind className="h-3.5 w-3.5" />}
              label="Wind"
              value={`${weather.wind_mph} mph`}
              sub={weather.wind_gust_mph != null ? `gusts ${weather.wind_gust_mph}` : undefined}
              highlight={risk?.dominant_factor === 'wind' || risk?.dominant_factor === 'load'}
            />
            <Stat
              icon={<CloudRain className="h-3.5 w-3.5" />}
              label="Rain"
              value={formatInchesPerHour(weather.rain_in_per_hr)}
              highlight={risk?.dominant_factor === 'rain'}
            />
            <Stat
              icon={<Snowflake className="h-3.5 w-3.5" />}
              label="Snow"
              value={formatInchesPerHour(weather.snow_in_per_hr)}
              highlight={risk?.dominant_factor === 'snow'}
            />
            <Stat
              icon={<Thermometer className="h-3.5 w-3.5" />}
              label={weatherCodeLabel(weather.weather_code)}
              value={weather.temperature_f != null ? `${weather.temperature_f}°F` : '—'}
            />
          </dl>
        ) : (
          <p className="mt-3 text-xs text-slate-500">Forecast unavailable for this checkpoint.</p>
        )}

        {risk?.applied_rule && (
          <p className="mt-2 rounded-md bg-slate-100 px-2 py-1 text-[11px] text-slate-700">
            Load rule: {risk.applied_rule}
          </p>
        )}
      </div>
    </Popup>
  )
}

function Stat({
  icon,
  label,
  value,
  sub,
  highlight,
}: {
  icon: React.ReactNode
  label: string
  value: string
  sub?: string
  highlight?: boolean
}) {
  return (
    <div className={highlight ? 'font-semibold text-slate-900' : ''}>
      <dt className="flex items-center gap-1 text-slate-500">
        {icon}
        {label}
      </dt>
      <dd>
        {value}
        {sub && <span className="ml-1 text-[10px] font-normal text-slate-500">{sub}</span>}
      </dd>
    </div>
  )
}
