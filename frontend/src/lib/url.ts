const PARAM = 'plan'

export function readPlanIdFromUrl(): string | null {
  return new URLSearchParams(window.location.search).get(PARAM)
}

export function writePlanIdToUrl(planId: string | null): void {
  const url = new URL(window.location.href)
  if (planId) url.searchParams.set(PARAM, planId)
  else url.searchParams.delete(PARAM)
  window.history.replaceState(null, '', url)
}
