import { describe, expect, it } from 'vitest'

import { formatDuration, formatMiles, formatPounds, toDateTimeLocal } from './format'

describe('format helpers', () => {
  it('formats durations in hours and minutes', () => {
    expect(formatDuration(0)).toBe('0 min')
    expect(formatDuration(45 * 60)).toBe('45 min')
    expect(formatDuration(3600)).toBe('1 h')
    expect(formatDuration(8.14 * 3600)).toBe('8 h 8 min')
  })

  it('formats distances and weights with separators', () => {
    expect(formatMiles(519.8)).toBe('520 mi')
    expect(formatMiles(519.8, 1)).toBe('519.8 mi')
    expect(formatPounds(42000)).toBe('42,000 lb')
  })

  it('produces datetime-local strings in local time', () => {
    const date = new Date(2026, 9, 20, 8, 5)
    expect(toDateTimeLocal(date)).toBe('2026-10-20T08:05')
  })
})
