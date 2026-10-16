import { Truck } from 'lucide-react'

export function AppHeader() {
  return (
    <header className="flex items-center gap-3 border-b border-slate-200 bg-white px-5 py-4">
      <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-slate-900 text-sky-300">
        <Truck className="h-5 w-5" aria-hidden />
      </div>
      <div className="min-w-0">
        <h1 className="text-[15px] leading-tight font-semibold text-slate-900">
          Weather-Aware Truck Routing
        </h1>
        <p className="truncate text-xs text-slate-500">
          Safest route by forecast wind, rain, snow and load
        </p>
      </div>
    </header>
  )
}
