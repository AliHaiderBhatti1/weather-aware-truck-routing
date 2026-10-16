import type { TripPlanRequest } from '@/lib/types'

import type { TripFormValues } from './schema'

/** Map validated form values to the API's request body. */
export function toRequest(values: TripFormValues): TripPlanRequest {
  return {
    origin: { name: values.origin!.full_name, lat: values.origin!.lat, lon: values.origin!.lon },
    destination: {
      name: values.destination!.full_name,
      lat: values.destination!.lat,
      lon: values.destination!.lon,
    },
    departure_time: new Date(values.departure).toISOString(),
    load_weight_lb: values.loadWeightLb,
    checkpoint_interval_miles: values.intervalMiles,
  }
}
