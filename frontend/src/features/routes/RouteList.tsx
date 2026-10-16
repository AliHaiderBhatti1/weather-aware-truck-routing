import { Award, ShieldAlert } from 'lucide-react'

import { Alert } from '@/components/ui'
import type { TripPlan } from '@/lib/types'

import { RouteCard } from './RouteCard'

interface RouteListProps {
  plan: TripPlan
  selectedRouteId: string | null
  onSelectRoute: (routeId: string) => void
}

export function RouteList({ plan, selectedRouteId, onSelectRoute }: RouteListProps) {
  const recommended = plan.routes.find((r) => r.id === plan.recommended_route_id)
  return (
    <section className="flex flex-col gap-3" aria-label="Route options">
      {recommended ? (
        <div className="flex gap-2.5 rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-900">
          <Award className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
          <div>
            <p className="font-semibold">Take {recommended.name}</p>
            {plan.recommendation_reasons.length > 0 && (
              <p className="mt-0.5 text-[13px] leading-snug">
                Chosen for {plan.recommendation_reasons.join('; ')}.
              </p>
            )}
          </div>
        </div>
      ) : (
        <div className="flex gap-2.5 rounded-xl border border-violet-200 bg-violet-50 p-3 text-sm text-violet-900">
          <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
          <div>
            <p className="font-semibold">No route is safe to drive at this departure time</p>
            <p className="mt-0.5 text-[13px] leading-snug">
              Every option crosses No-Travel conditions. Try a later departure or a lighter load.
            </p>
          </div>
        </div>
      )}

      {plan.warnings.map((warning) => (
        <Alert key={warning} tone="warning">
          {warning}
        </Alert>
      ))}

      {plan.routes.map((route) => (
        <RouteCard
          key={route.id}
          route={route}
          selected={route.id === selectedRouteId}
          onSelect={() => onSelectRoute(route.id)}
        />
      ))}
    </section>
  )
}
