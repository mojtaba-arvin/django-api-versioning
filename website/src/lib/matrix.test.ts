import { describe, expect, it } from 'vitest'
import { buildMatrix, lifecycleResponse } from './matrix'

describe('buildMatrix', () => {
  it('serves a forward segment from its version to the max', () => {
    const r = buildMatrix(
      [{ id: 'a', view: 'InvoiceDetailView', kind: 'forward', version: 2 }],
      1,
      3,
    )
    expect(r.cells.map((c) => c?.view ?? null)).toEqual([
      null,
      'InvoiceDetailView',
      'InvoiceDetailView',
    ])
  })

  it('hands over to the next forward declaration', () => {
    const r = buildMatrix(
      [
        { id: 'a', view: 'V1', kind: 'forward', version: 1 },
        { id: 'b', view: 'V3', kind: 'forward', version: 3 },
      ],
      1,
      5,
    )
    expect(r.cells.map((c) => c?.view)).toEqual(['V1', 'V1', 'V3', 'V3', 'V3'])
  })

  it('reports gaps and out-of-range versions', () => {
    const r = buildMatrix(
      [
        { id: 'a', view: 'Ranking', kind: 'set', versions: [2, 4] },
        { id: 'b', view: 'TooHigh', kind: 'forward', version: 9 },
      ],
      1,
      5,
    )
    expect(r.errors[0]).toMatch(/InvalidVersionError/)
    expect(r.warnings.some((w) => w.includes('v3'))).toBe(true)
  })
})

describe('lifecycleResponse', () => {
  const now = new Date('2026-11-17T00:00:00Z')
  it('returns 410 after sunset', () => {
    expect(
      lifecycleResponse({ status: 'retired', sunset: '2025-01-01' }, now).status,
    ).toBe(410)
  })
  it('adds Deprecation and Sunset headers', () => {
    const r = lifecycleResponse(
      {
        status: 'deprecated',
        deprecated_at: '2026-01-01T00:00:00+00:00',
        sunset: '2027-06-01',
      },
      now,
    )
    expect(r.status).toBe(200)
    expect(r.headers.map(([k]) => k)).toEqual(['Deprecation', 'Sunset'])
  })
  it('announces a retired version that is still before its sunset', () => {
    const r = lifecycleResponse(
      { status: 'retired', sunset: '2027-06-01' },
      now,
    )
    expect(r.status).toBe(200)
    expect(r.headers.map(([k]) => k)).toEqual(['Sunset'])
  })
  it('adds Deprecation for a retired version with deprecated_at', () => {
    const r = lifecycleResponse(
      {
        status: 'retired',
        deprecated_at: '2026-01-01T00:00:00+00:00',
        sunset: '2027-06-01',
      },
      now,
    )
    expect(r.status).toBe(200)
    expect(r.headers.map(([k]) => k)).toEqual(['Deprecation', 'Sunset'])
  })
  it('adds no headers for an active version', () => {
    const r = lifecycleResponse({ status: 'active', sunset: '2027-06-01' }, now)
    expect(r.status).toBe(200)
    expect(r.headers).toEqual([])
  })
})
