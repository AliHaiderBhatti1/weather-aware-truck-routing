import { useEffect, useState } from 'react'

const STEPS: { after: number; label: string }[] = [
  { after: 0, label: 'Finding three routes…' },
  { after: 1500, label: 'Dropping checkpoints and computing ETAs…' },
  { after: 2500, label: 'Fetching forecasts at every checkpoint…' },
  { after: 5000, label: 'Scoring wind, rain and snow against your load…' },
  { after: 9000, label: 'The weather provider is slow right now, still working…' },
]

/** Elapsed-time based status text while a plan request is in flight. */
export function usePlanningProgress(pending: boolean): string | null {
  const [startedAt, setStartedAt] = useState<number | null>(null)
  const [now, setNow] = useState(() => Date.now())

  // Derive the start time from the pending flag during render (no effect needed).
  if (pending && startedAt === null) setStartedAt(Date.now())
  if (!pending && startedAt !== null) setStartedAt(null)

  useEffect(() => {
    if (!pending) return
    const handle = window.setInterval(() => setNow(Date.now()), 250)
    return () => window.clearInterval(handle)
  }, [pending])

  if (!pending || startedAt === null) return null
  const elapsed = Math.max(0, now - startedAt)
  let label = STEPS[0].label
  for (const step of STEPS) if (elapsed >= step.after) label = step.label
  return label
}
