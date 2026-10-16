import { AppHeader } from '@/components/AppHeader'
import { ApiStatusBanner } from '@/features/health/ApiStatusBanner'

export default function App() {
  return (
    <div className="flex h-dvh flex-col lg:flex-row">
      <aside className="flex w-full shrink-0 flex-col border-b border-slate-200 bg-white lg:h-full lg:w-[440px] lg:border-r lg:border-b-0">
        <AppHeader />
        <ApiStatusBanner />
        <div className="flex-1 overflow-y-auto p-4">
          <p className="text-sm text-slate-500">Trip form coming next.</p>
        </div>
      </aside>
      <main className="relative min-h-[55dvh] flex-1 bg-slate-200 lg:min-h-0" aria-label="Map" />
    </div>
  )
}
