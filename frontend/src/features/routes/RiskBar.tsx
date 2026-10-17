import { RISK_LEVELS, RISK_META, type RiskLevel, UNKNOWN_RISK_COLOR } from '@/lib/risk'

interface RiskBarProps {
  milesByLevel: Record<RiskLevel, number>
  unknownMiles?: number
  className?: string
}

/** Stacked bar: share of route miles at each risk level, sorted by severity (not position). */
export function RiskBar({ milesByLevel, unknownMiles = 0, className }: RiskBarProps) {
  const parts = [
    ...RISK_LEVELS.map((level) => ({
      key: level,
      label: RISK_META[level].label,
      miles: milesByLevel[level] ?? 0,
      color: RISK_META[level].color,
    })),
    { key: 'unknown', label: 'No forecast', miles: unknownMiles, color: UNKNOWN_RISK_COLOR },
  ].filter((part) => part.miles > 0)
  const total = parts.reduce((sum, part) => sum + part.miles, 0) || 1

  return (
    <div
      className={`flex h-2 w-full overflow-hidden rounded-full bg-slate-100 ${className ?? ''}`}
      role="img"
      aria-label={parts.map((p) => `${p.label}: ${Math.round(p.miles)} mi`).join(', ')}
    >
      {parts.map((part) => (
        <div
          key={part.key}
          style={{ width: `${(part.miles / total) * 100}%`, backgroundColor: part.color }}
          title={`${part.label}: ${Math.round(part.miles)} mi`}
        />
      ))}
    </div>
  )
}
