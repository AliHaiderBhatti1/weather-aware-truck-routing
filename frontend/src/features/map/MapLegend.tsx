import { RISK_LEVELS, RISK_META, THRESHOLDS } from '@/lib/risk'

export function MapLegend() {
  return (
    <div className="shadow-panel pointer-events-auto rounded-xl border border-slate-200 bg-white/95 p-3 backdrop-blur">
      <p className="text-[11px] font-semibold tracking-wide text-slate-500 uppercase">
        Weather risk
      </p>
      <ul className="mt-2 flex flex-col gap-1">
        {RISK_LEVELS.map((level) => (
          <li key={level} className="flex items-center gap-2 text-xs text-slate-700">
            <span
              className="h-2.5 w-5 rounded-sm"
              style={{ backgroundColor: RISK_META[level].color }}
            />
            <span className="w-16 font-medium">{RISK_META[level].label}</span>
            <span className="text-[10px] text-slate-500">{thresholdHint(level)}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

function thresholdHint(level: (typeof RISK_LEVELS)[number]): string {
  const w = THRESHOLDS.wind_mph
  switch (level) {
    case 'low':
      return `wind < ${w.moderate} mph`
    case 'moderate':
      return `${w.moderate}–${w.high - 1} mph`
    case 'high':
      return `${w.high}–${w.severe - 1} mph`
    case 'severe':
      return `${w.severe}–${w.no_travel - 1} mph`
    case 'no_travel':
      return `≥ ${w.no_travel} mph or load rule`
  }
}
