import { useMemo, useState } from 'react'
import {
  buildMatrix,
  describeDeclaration,
  type Declaration,
} from '../lib/matrix'

const PATH = 'invoices/<int:invoice_id>/'

const PRESETS: { name: string; blurb: string; min: number; max: number; decls: Declaration[] }[] = [
  {
    name: 'Forward segment',
    blurb: 'One view introduced in v2, reused by every later version.',
    min: 1,
    max: 3,
    decls: [{ id: 'a', view: 'InvoiceDetailView', kind: 'forward', version: 2 }],
  },
  {
    name: 'Breaking change',
    blurb: 'A new view takes over from v3; v1–v2 keep the original.',
    min: 1,
    max: 5,
    decls: [
      { id: 'a', view: 'InvoiceV1', kind: 'forward', version: 1 },
      { id: 'b', view: 'InvoiceV3', kind: 'forward', version: 3 },
    ],
  },
  {
    name: 'Explicit set',
    blurb: 'versions=[2, 4] — check_versions flags the v3 gap.',
    min: 1,
    max: 5,
    decls: [{ id: 'a', view: 'RankingView', kind: 'set', versions: [2, 4] }],
  },
  {
    name: 'Bounded legacy',
    blurb: 'ver_range(1, 3) retires the route after v3.',
    min: 1,
    max: 5,
    decls: [
      { id: 'a', view: 'LegacyView', kind: 'range', from: 1, to: 3 },
      { id: 'b', view: 'ModernView', kind: 'forward', version: 4 },
    ],
  },
]

const SWATCHES = [
  'bg-leaf text-ink',
  'bg-amber text-ink',
  'bg-[#b9c9ff] text-ink',
  'bg-rose text-ink',
  'bg-[#e0a6f5] text-ink',
]

let uid = 100

export function Playground() {
  const [presetIdx, setPresetIdx] = useState(1)
  const [min, setMin] = useState(PRESETS[1].min)
  const [max, setMax] = useState(PRESETS[1].max)
  const [decls, setDecls] = useState<Declaration[]>(PRESETS[1].decls)

  const result = useMemo(() => buildMatrix(decls, min, max), [decls, min, max])
  const colorOf = (id: string) =>
    SWATCHES[decls.findIndex((d) => d.id === id) % SWATCHES.length]

  const loadPreset = (i: number) => {
    setPresetIdx(i)
    setMin(PRESETS[i].min)
    setMax(PRESETS[i].max)
    setDecls(PRESETS[i].decls.map((d) => ({ ...d })))
  }

  const update = (id: string, next: Declaration) => {
    setPresetIdx(-1)
    setDecls((ds) => ds.map((d) => (d.id === id ? next : d)))
  }

  const addDecl = () => {
    setPresetIdx(-1)
    const n = decls.length + 1
    setDecls((ds) => [
      ...ds,
      {
        id: `d${uid++}`,
        view: `InvoiceView${n}`,
        kind: 'forward',
        version: Math.min(max, n),
      },
    ])
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[1.05fr_1fr]">
      {/* Left: declarations */}
      <div className="card p-5 sm:p-6">
        <div className="flex flex-wrap gap-2">
          {PRESETS.map((p, i) => (
            <button
              key={p.name}
              type="button"
              onClick={() => loadPreset(i)}
              className={`rounded-full border px-3 py-1 text-xs font-medium transition ${
                presetIdx === i
                  ? 'border-leaf bg-leaf/15 text-leaf-2'
                  : 'border-line text-mute hover:text-paper'
              }`}
            >
              {p.name}
            </button>
          ))}
        </div>
        <p className="mt-3 min-h-5 text-sm text-mute">
          {presetIdx >= 0 ? PRESETS[presetIdx].blurb : 'Custom configuration.'}
        </p>

        <div className="mt-5 grid grid-cols-2 gap-3">
          <Stepper label="API_MIN_VERSION" value={min} onChange={(v) => setMin(Math.min(v, max))} lo={1} hi={9} />
          <Stepper label="API_MAX_VERSION" value={max} onChange={(v) => setMax(Math.max(v, min))} lo={1} hi={9} />
        </div>

        <ul className="mt-5 space-y-3">
          {decls.map((d) => (
            <li key={d.id} className="rounded-xl border border-line bg-ink p-3">
              <div className="flex items-center gap-2">
                <span className={`h-3 w-3 shrink-0 rounded-sm ${colorOf(d.id)}`} aria-hidden />
                <input
                  aria-label="View class name"
                  value={d.view}
                  onChange={(e) =>
                    update(d.id, { ...d, view: e.target.value.replace(/\W/g, '') || 'View' })
                  }
                  className="min-w-0 flex-1 bg-transparent font-mono text-sm text-paper outline-none focus:text-leaf-2"
                />
                <select
                  aria-label="Declaration type"
                  value={d.kind}
                  onChange={(e) => {
                    const kind = e.target.value as Declaration['kind']
                    const base = { id: d.id, view: d.view }
                    const v = d.kind === 'forward' ? d.version : d.kind === 'range' ? d.from : d.versions[0] ?? 1
                    update(
                      d.id,
                      kind === 'forward'
                        ? { ...base, kind, version: v }
                        : kind === 'set'
                          ? { ...base, kind, versions: [v] }
                          : { ...base, kind, from: v, to: Math.min(max, v + 1) },
                    )
                  }}
                  className="rounded-md border border-line bg-ink-3 px-2 py-1 text-xs text-paper"
                >
                  <option value="forward">version=</option>
                  <option value="set">versions=[…]</option>
                  <option value="range">ver_range()</option>
                </select>
                <button
                  type="button"
                  aria-label={`Remove ${d.view}`}
                  onClick={() => {
                    setPresetIdx(-1)
                    setDecls((ds) => ds.filter((x) => x.id !== d.id))
                  }}
                  className="rounded-md px-2 py-1 text-mute hover:text-rose"
                >
                  ×
                </button>
              </div>

              <div className="mt-3 flex flex-wrap items-center gap-1.5">
                {d.kind === 'forward' && (
                  <MiniStepper value={d.version} onChange={(v) => update(d.id, { ...d, version: v })} />
                )}
                {d.kind === 'range' && (
                  <>
                    <MiniStepper value={d.from} onChange={(v) => update(d.id, { ...d, from: v })} />
                    <span className="text-xs text-mute">to</span>
                    <MiniStepper value={d.to} onChange={(v) => update(d.id, { ...d, to: v })} />
                  </>
                )}
                {d.kind === 'set' &&
                  Array.from({ length: 9 }, (_, i) => i + 1).map((v) => {
                    const on = d.versions.includes(v)
                    return (
                      <button
                        key={v}
                        type="button"
                        aria-pressed={on}
                        onClick={() =>
                          update(d.id, {
                            ...d,
                            versions: on ? d.versions.filter((x) => x !== v) : [...d.versions, v],
                          })
                        }
                        className={`h-7 w-7 rounded-md border font-mono text-xs ${
                          on ? 'border-leaf bg-leaf/20 text-leaf-2' : 'border-line text-mute'
                        } ${v > max || v < min ? 'opacity-40' : ''}`}
                      >
                        {v}
                      </button>
                    )
                  })}
              </div>
              <code className="mt-3 block truncate font-mono text-[12px] text-mute">
                {describeDeclaration(d, PATH)}
              </code>
            </li>
          ))}
        </ul>
        <button type="button" onClick={addDecl} className="btn btn-ghost mt-4 w-full justify-center !py-2">
          + Add declaration
        </button>
      </div>

      {/* Right: matrix */}
      <div className="card flex flex-col p-5 sm:p-6">
        <div className="flex items-center justify-between">
          <h3 className="font-mono text-sm text-paper">
            <span className="text-leaf">$</span> python manage.py check_versions
          </h3>
        </div>
        <p className="mt-1 font-mono text-xs text-mute">{PATH}</p>

        <div className="mt-5" role="table" aria-label="Version matrix">
          <div role="rowgroup">
            <div className="flex items-center gap-3 pb-2 font-mono text-[10px] uppercase tracking-wide text-mute" role="row">
              <span className="w-40 shrink-0" role="columnheader">Endpoint</span>
              <span className="flex-1" role="columnheader">Resolved view</span>
            </div>
          </div>
          <div role="rowgroup" className="space-y-2">
          {result.versions.map((v, i) => {
            const c = result.cells[i]
            return (
              <div key={v} role="row" className="flex items-center gap-3">
                <span role="cell" className="w-40 shrink-0 font-mono text-xs text-mute">
                  /api/v{v}/invoices/42/
                </span>
                <span role="cell" className="flex-1">
                  {c ? (
                    <span
                      className={`flex items-center justify-between rounded-md px-3 py-1.5 font-mono text-xs font-semibold transition-all ${colorOf(c.declId)}`}
                    >
                      <span className="truncate">{c.view}</span>
                      <span className="opacity-60">
                        {c.source === v ? 'declared' : `from v${c.source}`}
                      </span>
                    </span>
                  ) : (
                    <span className="block rounded-md border border-dashed border-line px-3 py-1.5 font-mono text-xs text-mute">
                      404 Not Found
                    </span>
                  )}
                </span>
              </div>
            )
          })}
          </div>
        </div>

        <div className="mt-6 space-y-2 border-t border-line pt-4 font-mono text-xs">
          {result.errors.map((e) => (
            <p key={e} className="text-rose">✗ {e}</p>
          ))}
          {result.warnings.map((w) => (
            <p key={w} className="text-amber">! {w}</p>
          ))}
          {!result.errors.length && !result.warnings.length && (
            <p className="text-leaf-2">✓ No gaps. Matrix is consistent.</p>
          )}
        </div>
        <p className="mt-auto pt-6 text-xs text-mute">
          Interactive illustration of the documented resolution rules. Run{' '}
          <code className="inline-code">check_versions</code> in your project for the real matrix.
        </p>
      </div>
    </div>
  )
}

function Stepper({
  label,
  value,
  onChange,
  lo,
  hi,
}: {
  label: string
  value: number
  onChange: (v: number) => void
  lo: number
  hi: number
}) {
  return (
    <div className="rounded-xl border border-line bg-ink px-3 py-2">
      <div className="font-mono text-[10px] tracking-wide text-mute">{label}</div>
      <div className="mt-1 flex items-center justify-between">
        <button
          type="button"
          aria-label={`Decrease ${label}`}
          onClick={() => onChange(Math.max(lo, value - 1))}
          className="h-7 w-7 rounded-md border border-line text-mute hover:text-paper"
        >
          −
        </button>
        <span className="font-mono text-lg text-paper">{value}</span>
        <button
          type="button"
          aria-label={`Increase ${label}`}
          onClick={() => onChange(Math.min(hi, value + 1))}
          className="h-7 w-7 rounded-md border border-line text-mute hover:text-paper"
        >
          +
        </button>
      </div>
    </div>
  )
}

function MiniStepper({ value, onChange }: { value: number; onChange: (v: number) => void }) {
  return (
    <span className="inline-flex items-center rounded-md border border-line">
      <button
        type="button"
        aria-label="Decrease version"
        onClick={() => onChange(Math.max(1, value - 1))}
        className="px-2 py-0.5 text-mute hover:text-paper"
      >
        −
      </button>
      <span className="min-w-8 text-center font-mono text-xs text-leaf-2">v{value}</span>
      <button
        type="button"
        aria-label="Increase version"
        onClick={() => onChange(Math.min(12, value + 1))}
        className="px-2 py-0.5 text-mute hover:text-paper"
      >
        +
      </button>
    </span>
  )
}
