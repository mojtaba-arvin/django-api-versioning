/**
 * A small in-browser model of how @endpoint declarations expand into
 * versioned routes. It powers the homepage playground and mirrors the rules
 * documented in the package README:
 *
 * - `version=N` starts a forward segment that serves N..max until the next
 *   forward declaration on the same route takes over.
 * - `versions=[...]` / `ver_range(a, b)` serve exactly the listed versions.
 * - Versions above API_MAX_VERSION raise InvalidVersionError.
 * - Versions below API_MIN_VERSION are skipped with a warning.
 * - On collision the higher source version wins; ties go to the last
 *   registration.
 */

export type Declaration =
  | { id: string; view: string; kind: 'forward'; version: number }
  | { id: string; view: string; kind: 'set'; versions: number[] }
  | { id: string; view: string; kind: 'range'; from: number; to: number }

export type Cell = { declId: string; view: string; source: number } | null

export type MatrixResult = {
  versions: number[]
  cells: Cell[]
  errors: string[]
  warnings: string[]
}

export function declarationVersions(d: Declaration): number[] {
  if (d.kind === 'set') return [...new Set(d.versions)].sort((a, b) => a - b)
  if (d.kind === 'range') {
    const out: number[] = []
    for (let v = d.from; v <= d.to; v++) out.push(v)
    return out
  }
  return [d.version]
}

export function describeDeclaration(d: Declaration, path: string): string {
  if (d.kind === 'forward')
    return `@endpoint("${path}", version=${d.version})`
  if (d.kind === 'set')
    return `@endpoint("${path}", versions=[${declarationVersions(d).join(', ')}])`
  return `@endpoint("${path}", versions=ver_range(${d.from}, ${d.to}))`
}

export function buildMatrix(
  decls: Declaration[],
  min: number,
  max: number,
): MatrixResult {
  const versions: number[] = []
  for (let v = min; v <= max; v++) versions.push(v)
  const errors: string[] = []
  const warnings: string[] = []
  const valid: Declaration[] = []

  for (const d of decls) {
    if (d.kind === 'range' && d.from > d.to) {
      errors.push(
        `VersionRangeError: ver_range(${d.from}, ${d.to}) is empty for ${d.view}.`,
      )
      continue
    }
    const vs = declarationVersions(d)
    const tooHigh = vs.filter((v) => v > max)
    if (tooHigh.length) {
      errors.push(
        `InvalidVersionError: ${d.view} declares v${tooHigh.join(', v')} above API_MAX_VERSION=${max}.`,
      )
      continue
    }
    const tooLow = vs.filter((v) => v < min)
    if (tooLow.length) {
      warnings.push(
        `${d.view}: v${tooLow.join(', v')} below API_MIN_VERSION=${min} skipped.`,
      )
    }
    valid.push(d)
  }

  const forwardStarts = valid
    .filter((d) => d.kind === 'forward')
    .map((d) => (d as { version: number }).version)

  const cells: Cell[] = versions.map((v) => {
    let winner: Cell = null
    for (const d of valid) {
      let source: number | null = null
      if (d.kind === 'forward') {
        const start = d.version
        const nextStart = forwardStarts
          .filter((s) => s > start)
          .reduce((a, b) => Math.min(a, b), Infinity)
        if (v >= start && v < nextStart) source = start
      } else if (declarationVersions(d).includes(v)) {
        source = v
      }
      if (source === null) continue
      // Higher source version wins; ties go to the later registration.
      if (!winner || source >= winner.source) {
        winner = { declId: d.id, view: d.view, source }
      }
    }
    return winner
  })

  // check_versions-style gap detection: uncovered versions inside the span.
  const covered = cells
    .map((c, i) => (c ? versions[i] : null))
    .filter((v): v is number => v !== null)
  if (covered.length) {
    const lo = covered[0]
    const hi = covered[covered.length - 1]
    const gaps = versions.filter(
      (v, i) => v > lo && v < hi && cells[i] === null,
    )
    if (gaps.length) {
      warnings.push(`Gap inside endpoint span: v${gaps.join(', v')} return 404.`)
    }
  }

  return { versions, cells, errors, warnings }
}

/* ------------------------------------------------------------------ */
/* Lifecycle headers (RFC 9745 Deprecation / RFC 8594 Sunset)          */
/* ------------------------------------------------------------------ */

export type LifecycleEntry = {
  status: 'active' | 'deprecated' | 'retired'
  deprecated_at?: string
  sunset?: string
}

export type LifecycleResponse = {
  status: number
  statusText: string
  headers: [string, string][]
}

export function lifecycleResponse(
  entry: LifecycleEntry | undefined,
  now: Date,
): LifecycleResponse {
  const headers: [string, string][] = []
  const sunset = entry?.sunset ? new Date(`${entry.sunset}T00:00:00Z`) : null

  if (sunset && sunset.getTime() <= now.getTime()) {
    headers.push(['Sunset', sunset.toUTCString()])
    return { status: 410, statusText: 'Gone', headers }
  }
  // Mirrors LifecycleMiddleware: only deprecated and retired versions are
  // announced; a retired version with a future sunset is still served.
  if (entry && (entry.status === 'deprecated' || entry.status === 'retired')) {
    if (entry.deprecated_at) {
      const epoch = Math.floor(new Date(entry.deprecated_at).getTime() / 1000)
      headers.push(['Deprecation', `@${epoch}`])
    }
    if (sunset) headers.push(['Sunset', sunset.toUTCString()])
  }
  return { status: 200, statusText: 'OK', headers }
}
