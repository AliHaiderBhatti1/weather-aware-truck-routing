/** Risk vocabulary shared with the API. Order matters: index == numeric score. */
export const RISK_LEVELS = ['low', 'moderate', 'high', 'severe', 'no_travel'] as const
export type RiskLevel = (typeof RISK_LEVELS)[number]

export interface RiskMeta {
  label: string
  shortLabel: string
  color: string
  /** Tailwind classes for badges / chips. */
  badge: string
  description: string
}

export const RISK_META: Record<RiskLevel, RiskMeta> = {
  low: {
    label: 'Low',
    shortLabel: 'Low',
    color: '#16a34a',
    badge: 'bg-green-50 text-green-700 ring-green-600/20',
    description: 'Normal driving conditions.',
  },
  moderate: {
    label: 'Moderate',
    shortLabel: 'Mod',
    color: '#eab308',
    badge: 'bg-yellow-50 text-yellow-800 ring-yellow-600/20',
    description: 'Stay alert; conditions may slow you down.',
  },
  high: {
    label: 'High',
    shortLabel: 'High',
    color: '#f97316',
    badge: 'bg-orange-50 text-orange-700 ring-orange-600/20',
    description: 'Reduce speed and increase following distance.',
  },
  severe: {
    label: 'Severe',
    shortLabel: 'Sev',
    color: '#dc2626',
    badge: 'bg-red-50 text-red-700 ring-red-600/20',
    description: 'Dangerous for a loaded truck; consider delaying.',
  },
  no_travel: {
    label: 'No Travel',
    shortLabel: 'Stop',
    color: '#6d28d9',
    badge: 'bg-violet-50 text-violet-700 ring-violet-600/20',
    description: 'Do not travel through this checkpoint at this time.',
  },
}

export const UNKNOWN_RISK_COLOR = '#94a3b8'

export function riskScore(level: RiskLevel): number {
  return RISK_LEVELS.indexOf(level)
}

export function riskColor(level: RiskLevel | null | undefined): string {
  return level ? RISK_META[level].color : UNKNOWN_RISK_COLOR
}

export function levelFromScore(score: number): RiskLevel {
  return RISK_LEVELS[Math.max(0, Math.min(RISK_LEVELS.length - 1, Math.round(score)))]
}

/** Thresholds from the brief, kept here so the legend can explain itself. */
export const THRESHOLDS = {
  wind_mph: { moderate: 25, high: 35, severe: 45, no_travel: 55 },
  rain_in_per_hr: { moderate: 0.1, high: 0.25, severe: 0.5, no_travel: 1.0 },
  snow_in_per_hr: { moderate: 0.5, high: 1.0, severe: 2.0, no_travel: 3.0 },
} as const
