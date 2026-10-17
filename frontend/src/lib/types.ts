import type { RiskLevel } from './risk'

export interface Place {
  name: string
  full_name: string
  lat: number
  lon: number
  kind?: string
}

export type CheckpointInterval = 10 | 25 | 50

export interface PlaceInput {
  query?: string
  name?: string
  lat?: number
  lon?: number
}

export interface TripPlanRequest {
  origin: PlaceInput
  destination: PlaceInput
  departure_time: string
  load_weight_lb: number
  checkpoint_interval_miles: CheckpointInterval
}

export interface CheckpointWeather {
  wind_mph: number
  wind_gust_mph: number | null
  rain_in_per_hr: number
  snow_in_per_hr: number
  temperature_f: number | null
  weather_code: number | null
}

export interface CheckpointRisk {
  level: RiskLevel
  label: string
  score: number
  wind_level: RiskLevel
  rain_level: RiskLevel
  snow_level: RiskLevel
  dominant_factor: 'wind' | 'rain' | 'snow' | 'load' | 'none'
  applied_rule: string | null
}

export interface Checkpoint {
  index: number
  lat: number
  lon: number
  distance_from_start_miles: number
  segment_miles: number
  eta: string
  weather: CheckpointWeather | null
  risk: CheckpointRisk | null
}

export interface RouteSummary {
  max_level: RiskLevel
  average_risk: number
  travel_advised: boolean
  no_travel_miles: number
  severe_miles: number
  high_miles: number
  /** Miles represented by checkpoints without a forecast. */
  unknown_miles: number
  miles_by_level: Record<RiskLevel, number>
}

export interface PlannedRoute {
  id: string
  name: string
  source: string
  rank: number
  recommended: boolean
  distance_miles: number
  duration_seconds: number
  arrival_time: string
  geometry: { type: 'LineString'; coordinates: [number, number][] }
  summary: RouteSummary
  checkpoints: Checkpoint[]
}

export interface TripPlan {
  id: string
  created_at: string
  request: {
    origin: Place
    destination: Place
    departure_time: string
    load_weight_lb: number
    checkpoint_interval_miles: CheckpointInterval
  }
  recommended_route_id: string | null
  recommendation_reasons: string[]
  warnings: string[]
  routes: PlannedRoute[]
  bounds: [[number, number], [number, number]]
  forecast_window: { start: string; end: string; hours: number }
}

export interface HeatmapPoint {
  lat: number
  lon: number
  /** Risk level per hour (0 = Low ... 4 = No Travel); null where no forecast exists. */
  levels: (number | null)[]
  wind_mph: (number | null)[]
}

export interface Heatmap {
  /** False when the weather service failed for part of the corridor. */
  complete?: boolean
  start: string
  hours: string[]
  points: HeatmapPoint[]
}

export interface Health {
  status: string
  version: string
  providers: { routing: string; weather: string }
}
