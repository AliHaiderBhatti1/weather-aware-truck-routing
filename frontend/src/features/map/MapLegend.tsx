import { RISK_LEVELS, RISK_META, type RiskLevel, THRESHOLDS } from '@/lib/risk'

type Factor = keyof typeof THRESHOLDS

const FACTORS: { key: Factor; label: string; unit: string; digits: number }[] = [
  { key: 'wind_mph', label: 'Wind', unit: 'mph', digits: 0 },
  { key: 'rain_in_per_hr', label: 'Rain', unit: 'in/hr', digits: 2 },
  { key: 'snow_in_per_hr', label: 'Snow', unit: 'in/hr', digits: 1 },
]

/**
 * Lower bound that puts a reading at ``level``, as written in the brief:
 * wind is inclusive at every band (≥ 55 is No Travel), while rain and snow
 * only become No Travel strictly above the top Severe value.
 */
function bandLabel(factor: Factor, level: RiskLevel, digits: number): string {
  const t = THRESHOLDS[factor]
  const fmt = (value: number) => value.toFixed(digits)
  switch (level) {
    case 'low':
      return `< ${fmt(t.moderate)}`
    case 'no_travel':
      return factor === 'wind_mph' ? `≥ ${fmt(t.no_travel)}` : `> ${fmt(t.no_travel)}`
    default:
      return `≥ ${fmt(t[level])}`
  }
}

export function MapLegend() {
  return (
    <div className="shadow-panel pointer-events-auto rounded-xl border border-slate-200 bg-white/95 p-3 backdrop-blur">
      <table className="text-[11px] text-slate-700">
        <caption className="mb-1.5 text-left text-[11px] font-semibold tracking-wide text-slate-500 uppercase">
          Weather risk
        </caption>
        <thead>
          <tr className="text-[10px] text-slate-500">
            <th className="pb-1 text-left font-medium" scope="col">
              <span className="sr-only">Level</span>
            </th>
            {FACTORS.map((factor) => (
              <th key={factor.key} className="pb-1 pl-3 text-right font-medium" scope="col">
                {factor.label}
                <span className="block font-normal text-slate-400">{factor.unit}</span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {RISK_LEVELS.map((level) => (
            <tr key={level}>
              <th className="py-0.5 pr-1 text-left font-medium" scope="row">
                <span className="flex items-center gap-2">
                  <span
                    className="h-2.5 w-4 shrink-0 rounded-sm"
                    style={{ backgroundColor: RISK_META[level].color }}
                    aria-hidden
                  />
                  {RISK_META[level].label}
                </span>
              </th>
              {FACTORS.map((factor) => (
                <td key={factor.key} className="py-0.5 pl-3 text-right tabular-nums">
                  {bandLabel(factor.key, level, factor.digits)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      <p className="mt-1.5 max-w-[15rem] text-[10px] leading-snug text-slate-500">
        A checkpoint takes its worst factor. Loads over 30,000 lb (45+ mph) or 40,000 lb (35+ mph)
        raise wind to No Travel or Severe.
      </p>
    </div>
  )
}
