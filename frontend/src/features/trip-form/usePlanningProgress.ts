import { useEffect, useState } from 'react'

const STEPS: { after: number; label: string }[] = [
  { after: 0, label: 'Finding three routes…' },
  { after: 1500, label: 'Dropping checkpoints and computing ETAs…' },
  { after: 2500, label: 'Fetching forecasts at every checkpoint…' },
  { after: 5000, label: 'Scoring wind, rain and snow against your load…' },
  { after: 9000, label: 'The weather provider is slow right now, still working…' },
]

const TICK_MS = 250

/** Elapsed-time based status text while a plan request is in flight. */
export function usePlanningProgress(pending: boolean): string | null {
  const [elapsed, setElapsed] = useState(0)

  useEffect(() => {
    if (!pending) return
    const started = performance.now()
    const handle = window.setInterval(() => setElapsed(performance.now() - started), TICK_MS)
    return () => {
      window.clearInterval(handle)
      window.setTimeout(() => setElapsed(0), 0)
    }
  }, [pending])

  if (!pending) return null
  let label = STEPS[0].label
  for (const step of STEPS) if (elapsed >= step.after) label = step.label
  return label
}
