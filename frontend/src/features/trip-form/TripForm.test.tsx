import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { toRequest } from './toRequest'
import { TripForm } from './TripForm'

function renderForm(onSubmit = vi.fn()) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={client}>
      <TripForm onSubmit={onSubmit} pending={false} error={null} />
    </QueryClientProvider>,
  )
  return onSubmit
}

describe('TripForm', () => {
  it('requires both places to be chosen from the list', async () => {
    const onSubmit = renderForm()
    await userEvent.click(screen.getByRole('button', { name: /plan routes/i }))

    expect(await screen.findByText('Choose an origin from the list.')).toBeInTheDocument()
    expect(screen.getByText('Choose a destination from the list.')).toBeInTheDocument()
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('rejects an out-of-range load weight', async () => {
    const onSubmit = renderForm()
    const load = screen.getByLabelText('Load weight')
    await userEvent.clear(load)
    await userEvent.type(load, '250000')
    await userEvent.click(screen.getByRole('button', { name: /plan routes/i }))

    await waitFor(() => expect(screen.getByText(/cannot exceed 200,000 lb/i)).toBeInTheDocument())
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('builds the API request from form values', () => {
    const request = toRequest({
      origin: { name: 'Denver', full_name: 'Denver, CO', lat: 39.74, lon: -104.99 },
      destination: { name: 'SLC', full_name: 'Salt Lake City, UT', lat: 40.76, lon: -111.89 },
      departure: '2026-10-20T08:00',
      loadWeightLb: 42000,
      intervalMiles: 10,
    })

    expect(request.origin).toEqual({ name: 'Denver, CO', lat: 39.74, lon: -104.99 })
    expect(request.load_weight_lb).toBe(42000)
    expect(request.checkpoint_interval_miles).toBe(10)
    expect(new Date(request.departure_time).getTime()).toBe(new Date('2026-10-20T08:00').getTime())
  })
})
