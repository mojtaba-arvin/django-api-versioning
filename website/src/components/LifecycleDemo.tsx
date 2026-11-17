import { useEffect, useState } from 'react'
import { lifecycleResponse, type LifecycleEntry } from '../lib/matrix'

const LIFECYCLE: Record<number, LifecycleEntry> = {
  1: { status: 'retired', sunset: '2025-01-01' },
  2: {
    status: 'deprecated',
    deprecated_at: '2026-01-01T00:00:00+00:00',
    sunset: '2027-06-01',
  },
  3: { status: 'active' },
}

const STATUS_STYLE: Record<LifecycleEntry['status'], string> = {
  retired: 'bg-rose/15 text-rose border-rose/40',
  deprecated: 'bg-amber/15 text-amber border-amber/40',
  active: 'bg-leaf/15 text-leaf-2 border-leaf/40',
}

export function LifecycleDemo() {
  const [version, setVersion] = useState(2)
  // Fixed initial date keeps SSR and hydration identical; the live clock takes over in the browser.
  const [now, setNow] = useState(() => new Date('2026-11-17T00:00:00Z'))
  useEffect(() => setNow(new Date()), [])

  const entry = LIFECYCLE[version]
  const res = lifecycleResponse(entry, now)

  return (
    <div className="card overflow-hidden">
      <div className="flex flex-wrap items-center gap-2 border-b border-line p-4">
        {Object.entries(LIFECYCLE).map(([v, e]) => (
          <button
            key={v}
            type="button"
            onClick={() => setVersion(Number(v))}
            aria-pressed={version === Number(v)}
            className={`flex items-center gap-2 rounded-lg border px-3 py-1.5 font-mono text-xs transition ${
              version === Number(v)
                ? 'border-paper/60 bg-ink-3 text-paper'
                : 'border-line text-mute hover:text-paper'
            }`}
          >
            v{v}
            <span className={`rounded border px-1.5 py-px text-[10px] uppercase ${STATUS_STYLE[e.status]}`}>
              {e.status}
            </span>
          </button>
        ))}
      </div>
      <div className="space-y-1 p-5 font-mono text-[13px] leading-relaxed">
        <p className="text-mute">
          <span className="text-leaf-2">GET</span> /api/v{version}/invoices/42/ HTTP/1.1
        </p>
        <div className="my-3 h-px bg-line" />
        <p>
          HTTP/1.1{' '}
          <span className={res.status === 410 ? 'text-rose' : 'text-leaf-2'}>
            {res.status} {res.statusText}
          </span>
        </p>
        <p className="text-mute">Content-Type: application/json</p>
        {res.headers.map(([k, v]) => (
          <p key={k}>
            <span className="text-amber">{k}</span>: <span className="text-paper">{v}</span>
          </p>
        ))}
        {res.headers.length === 0 && (
          <p className="text-mute italic"># active — no lifecycle headers added</p>
        )}
      </div>
    </div>
  )
}
