import { formatClock } from '@/lib/format'
import { RISK_META } from '@/lib/risk'
import type { PlannedRoute } from '@/lib/types'

export function CheckpointList({ route }: { route: PlannedRoute }) {
  return (
    <div className="overflow-hidden rounded-lg border border-slate-200">
      <table className="w-full text-left text-[11px]">
        <thead className="bg-slate-50 text-slate-500">
          <tr>
            <th className="px-2 py-1.5 font-medium">Mile</th>
            <th className="px-2 py-1.5 font-medium">ETA</th>
            <th className="px-2 py-1.5 font-medium">Wind</th>
            <th className="px-2 py-1.5 font-medium">Rain</th>
            <th className="px-2 py-1.5 font-medium">Snow</th>
            <th className="px-2 py-1.5 font-medium">Risk</th>
          </tr>
        </thead>
        <tbody>
          {route.checkpoints.map((cp) => {
            const level = cp.risk?.level
            return (
              <tr key={cp.index} className="border-t border-slate-100 text-slate-700">
                <td className="px-2 py-1 tabular-nums">
                  {Math.round(cp.distance_from_start_miles)}
                </td>
                <td className="px-2 py-1 whitespace-nowrap tabular-nums">{formatClock(cp.eta)}</td>
                <td className="px-2 py-1 tabular-nums">
                  {cp.weather ? `${Math.round(cp.weather.wind_mph)}` : '—'}
                </td>
                <td className="px-2 py-1 tabular-nums">
                  {cp.weather ? cp.weather.rain_in_per_hr.toFixed(2) : '—'}
                </td>
                <td className="px-2 py-1 tabular-nums">
                  {cp.weather ? cp.weather.snow_in_per_hr.toFixed(2) : '—'}
                </td>
                <td className="px-2 py-1">
                  <span className="inline-flex items-center gap-1.5 font-medium">
                    <span
                      className="h-2 w-2 rounded-full"
                      style={{ backgroundColor: level ? RISK_META[level].color : '#94a3b8' }}
                    />
                    {level ? RISK_META[level].shortLabel : 'n/a'}
                  </span>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
      <p className="bg-slate-50 px-2 py-1 text-[10px] text-slate-500">
        Wind in mph · rain and snow in inches per hour
      </p>
    </div>
  )
}
