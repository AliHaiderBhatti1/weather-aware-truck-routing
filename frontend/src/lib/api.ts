import type { Health, Heatmap, Place, TripPlan, TripPlanRequest } from './types'

const BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '')

export class ApiError extends Error {
  readonly code: string
  readonly status: number
  readonly details: unknown

  constructor(status: number, code: string, message: string, details?: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.details = details
  }

  /** Flatten DRF field errors into "field: message" lines for display. */
  get fieldMessages(): string[] {
    if (!this.details || typeof this.details !== 'object') return []
    const lines: string[] = []
    const walk = (value: unknown, path: string[]) => {
      if (Array.isArray(value)) {
        value.forEach((item) => walk(item, path))
      } else if (value && typeof value === 'object') {
        Object.entries(value).forEach(([key, nested]) => walk(nested, [...path, key]))
      } else if (typeof value === 'string') {
        lines.push(path.length ? `${path.join('.')}: ${value}` : value)
      }
    }
    walk(this.details, [])
    return lines
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      ...init,
      headers: { Accept: 'application/json', 'Content-Type': 'application/json', ...init?.headers },
    })
  } catch (error) {
    throw new ApiError(0, 'network_error', 'Could not reach the planning API.', error)
  }

  const body: unknown = await response.json().catch(() => null)
  if (!response.ok) {
    const envelope = (body as { error?: { code?: string; message?: string; details?: unknown } })
      ?.error
    throw new ApiError(
      response.status,
      envelope?.code ?? 'error',
      envelope?.message ?? `Request failed with HTTP ${response.status}`,
      envelope?.details,
    )
  }
  return body as T
}

export const api = {
  health: () => request<Health>('/api/health/'),
  geocode: (q: string, signal?: AbortSignal) =>
    request<Place[]>(`/api/geocode/?${new URLSearchParams({ q, limit: '6' })}`, { signal }),
  createPlan: (body: TripPlanRequest) =>
    request<TripPlan>('/api/trips/', { method: 'POST', body: JSON.stringify(body) }),
  getPlan: (id: string) => request<TripPlan>(`/api/trips/${id}/`),
  getHeatmap: (id: string) => request<Heatmap>(`/api/trips/${id}/heatmap/`),
}
