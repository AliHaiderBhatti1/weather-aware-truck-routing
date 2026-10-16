import { describe, expect, it } from 'vitest'

import { levelFromScore, RISK_LEVELS, riskColor, riskScore, UNKNOWN_RISK_COLOR } from './risk'

describe('risk helpers', () => {
  it('scores levels by their position', () => {
    expect(RISK_LEVELS.map(riskScore)).toEqual([0, 1, 2, 3, 4])
  })

  it('maps scores back to levels with clamping', () => {
    expect(levelFromScore(0)).toBe('low')
    expect(levelFromScore(2.6)).toBe('severe')
    expect(levelFromScore(99)).toBe('no_travel')
    expect(levelFromScore(-1)).toBe('low')
  })

  it('falls back to a neutral colour when there is no data', () => {
    expect(riskColor(null)).toBe(UNKNOWN_RISK_COLOR)
    expect(riskColor('severe')).toMatch(/^#/)
  })
})
