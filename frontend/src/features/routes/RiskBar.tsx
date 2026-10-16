import { RISK_LEVELS, RISK_META, type RiskLevel } from '@/lib/risk'

interface RiskBarProps {
  milesByLevel: Record<RiskLevel, number>
  totalMiles: number
  className?: string
}

/** Stacked bar: share of route miles at each risk level, in route order of severity. */
export function RiskBar({ milesByLevel, totalMiles, className }: RiskBarProps) {
  const total = totalMiles > 0 ? totalMiles : 1
  return (
    <div
      className={`flex h-2 w-full overflow-hidden rounded-full bg-slate-100 ${className ?? ''}`}
      role="img"
      aria-label={RISK_LEVELS.map((l) => `${RISK_META[l].label}: ${milesByLevel[l]} mi`).join(', ')}
    >
      {RISK_LEVELS.map((level) => {
        const share = (milesByLevel[level] ?? 0) / total
        if (share <= 0) return null
        return (
          <div
            key={level}
            style={{ width: `${share * 100}%`, backgroundColor: RISK_META[level].color }}
            title={`${RISK_META[level].label}: ${milesByLevel[level]} mi`}
          />
        )
      })}
    </div>
  )
}
