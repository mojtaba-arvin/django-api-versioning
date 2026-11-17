import { useState, type ReactNode } from 'react'
import { tokenize } from '../lib/highlight'

function highlight(code: string, lang: string): ReactNode[] {
  return tokenize(code, lang).map((t, i) =>
    t.cls ? (
      <span key={i} className={t.cls === 'tok-prompt' ? 'text-leaf select-none' : t.cls}>
        {t.text}
      </span>
    ) : (
      t.text
    ),
  )
}

export function CopyButton({ text, label = 'Copy' }: { text: string; label?: string }) {
  const [copied, setCopied] = useState(false)
  return (
    <button
      type="button"
      onClick={() => {
        navigator.clipboard?.writeText(text).then(() => {
          setCopied(true)
          setTimeout(() => setCopied(false), 1600)
        })
      }}
      className="rounded-md border border-line px-2 py-1 font-mono text-[11px] text-mute transition hover:border-leaf hover:text-leaf-2"
      aria-label={`${label} to clipboard`}
    >
      {copied ? 'Copied ✓' : label}
    </button>
  )
}

export function CodeBlock({
  code,
  lang = 'python',
  title,
  className = '',
}: {
  code: string
  lang?: 'python' | 'bash' | 'text'
  title?: string
  className?: string
}) {
  const copyText = code
    .split('\n')
    .map((l) => (l.startsWith('$ ') ? l.slice(2) : l))
    .join('\n')
  return (
    <div className={`card overflow-hidden ${className}`}>
      <div className="flex items-center justify-between border-b border-line bg-ink-3/60 px-4 py-2">
        <div className="flex items-center gap-2">
          <span className="flex gap-1.5" aria-hidden>
            <span className="h-2.5 w-2.5 rounded-full bg-line" />
            <span className="h-2.5 w-2.5 rounded-full bg-line" />
            <span className="h-2.5 w-2.5 rounded-full bg-line" />
          </span>
          {title && (
            <span className="ml-2 font-mono text-xs text-mute">{title}</span>
          )}
        </div>
        <CopyButton text={copyText} />
      </div>
      <pre className="overflow-x-auto p-4 text-[13px] leading-relaxed text-paper">
        <code>{highlight(code, lang)}</code>
      </pre>
    </div>
  )
}
