import { Card, Skeleton } from '@/components/ui'

/** Placeholder while a shared plan link loads. */
export function PlanSkeleton() {
  return (
    <div className="flex flex-col gap-4" aria-busy="true" aria-label="Loading the shared plan">
      <Card className="flex flex-col gap-2 p-4">
        <Skeleton className="h-4 w-3/4" />
        <Skeleton className="h-3 w-1/2" />
      </Card>
      <Skeleton className="h-16 w-full rounded-xl" />
      {[0, 1, 2].map((key) => (
        <Card key={key} className="flex flex-col gap-3 p-4">
          <Skeleton className="h-4 w-2/3" />
          <Skeleton className="h-2 w-full" />
          <div className="grid grid-cols-4 gap-2">
            {[0, 1, 2, 3].map((cell) => (
              <Skeleton key={cell} className="h-8" />
            ))}
          </div>
        </Card>
      ))}
    </div>
  )
}
