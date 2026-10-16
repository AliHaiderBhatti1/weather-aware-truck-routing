import { z } from 'zod'

export const placeSchema = z.object({
  name: z.string().min(1),
  full_name: z.string().min(1),
  lat: z.number().min(-90).max(90),
  lon: z.number().min(-180).max(180),
})

export type PlaceValue = z.infer<typeof placeSchema>

export const MAX_LOAD_LB = 200_000
export const MAX_DAYS_AHEAD = 14
export const INTERVAL_OPTIONS = [10, 25, 50] as const

export type IntervalMiles = (typeof INTERVAL_OPTIONS)[number]

export interface TripFormValues {
  origin: PlaceValue | null
  destination: PlaceValue | null
  departure: string
  loadWeightLb: number
  intervalMiles: IntervalMiles
}

export const tripFormSchema: z.ZodType<TripFormValues, TripFormValues> = z
  .object({
    origin: placeSchema.nullable().refine((v) => v !== null, 'Choose an origin from the list.'),
    destination: placeSchema
      .nullable()
      .refine((v) => v !== null, 'Choose a destination from the list.'),
    departure: z.string().min(1, 'Pick a departure time.'),
    loadWeightLb: z
      .number({ error: 'Enter the load weight in pounds.' })
      .int('Whole pounds only.')
      .min(0, 'Load weight cannot be negative.')
      .max(MAX_LOAD_LB, `Load weight cannot exceed ${MAX_LOAD_LB.toLocaleString()} lb.`),
    intervalMiles: z.union([z.literal(10), z.literal(25), z.literal(50)]),
  })
  .superRefine((values, ctx) => {
    const departure = new Date(values.departure)
    if (Number.isNaN(departure.getTime())) {
      ctx.addIssue({ code: 'custom', path: ['departure'], message: 'Invalid date.' })
      return
    }
    const now = Date.now()
    if (departure.getTime() < now - 60 * 60 * 1000) {
      ctx.addIssue({ code: 'custom', path: ['departure'], message: 'Departure is in the past.' })
    }
    if (departure.getTime() > now + MAX_DAYS_AHEAD * 24 * 60 * 60 * 1000) {
      ctx.addIssue({
        code: 'custom',
        path: ['departure'],
        message: `Forecasts only cover the next ${MAX_DAYS_AHEAD} days.`,
      })
    }
    if (
      values.origin &&
      values.destination &&
      Math.abs(values.origin.lat - values.destination.lat) < 0.005 &&
      Math.abs(values.origin.lon - values.destination.lon) < 0.005
    ) {
      ctx.addIssue({
        code: 'custom',
        path: ['destination'],
        message: 'Destination must differ from the origin.',
      })
    }
  })
