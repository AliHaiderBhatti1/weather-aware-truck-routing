import { Loader2, WifiOff } from 'lucide-react'

import { useApiHealth } from './useApiHealth'

export function ApiStatusBanner() {
  const health = useApiHealth()
  if (health.isSuccess) return null

  if (health.isError) {
    return (
      <div className="flex items-center gap-2 border-b border-red-200 bg-red-50 px-4 py-2 text-xs text-red-800">
        <WifiOff className="h-3.5 w-3.5" aria-hidden />
        The planning API is unreachable. Check that the backend is running.
      </div>
    )
  }

  return (
    <div className="flex items-center gap-2 border-b border-amber-200 bg-amber-50 px-4 py-2 text-xs text-amber-900">
      <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden />
      Waking up the planning API. Free hosting sleeps when idle; this takes up to a minute.
    </div>
  )
}
