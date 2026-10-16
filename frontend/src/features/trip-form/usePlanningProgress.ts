import { useEffect, useRef, useState } from 'react'

const STEPS: { after: number; label: string }[] = [
  { after: 0, label: 'Finding three routes…' },
  { after: 1500, label: 'Dropping checkpoints and computing ETAs…' },
  { after: 2500, label: 'Fetching forecasts at every checkpoint…' },
  { after: 5000, label: 'Scoring wind, rain and snow against your load…' },
  { after: 9000, label: 'The weather provider is slow right now, still working…' },
]

/** Elapsed-time based status text while a plan request is in flight. */
export function usePlanningProgress(pending: boolean): string | null {
  const startedAt = useRef<number | null>(null)
  const [now, setNow] = useState(0)

  useEffect(() => {
    if (!pending) {
      startedAt.current = null
      return
    }
    startedAt.current = performance.now()
    const handle = window.setInterval(() => setNow(performance.now()), 250)
    return () => window.clearInterval(handle)
  }, [pending])

  if (!pending) return null
  const elapsed = startedAt.current === null ? 0 : Math.max(0, now - startedAt.current)
  let label = STEPS[0].label
  for (const step of STEPS) if (elapsed >= step.after) label = step.label
  return label
}
