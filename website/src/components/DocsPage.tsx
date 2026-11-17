import type { MouseEvent } from 'react'
import { Link } from '@tanstack/react-router'
import referenceMarkdown from '../../content/reference/index.md?raw'
import { renderReferenceMarkdown } from '../lib/reference-markdown'
import { SiteFooter, SiteHeader } from './Layout'

const reference = renderReferenceMarkdown(referenceMarkdown)

/** Copy handler for code blocks rendered from the canonical Reference Markdown. */
function handleCopy(e: MouseEvent<HTMLElement>) {
  const button = (e.target as HTMLElement).closest<HTMLButtonElement>('button[data-copy]')
  if (!button) return
  const code = button.closest('.reference-code')?.querySelector('pre')?.textContent ?? ''
  const copyText = code
    .split('\n')
    .map((line) => (line.startsWith('$ ') ? line.slice(2) : line))
    .join('\n')
  navigator.clipboard?.writeText(copyText).then(() => {
    button.textContent = 'Copied ✓'
    setTimeout(() => {
      button.textContent = 'Copy'
    }, 1600)
  })
}

export function DocsPage() {
  return (
    <>
      <SiteHeader />
      <main className="mx-auto grid max-w-6xl gap-12 px-5 py-16 lg:grid-cols-[200px_1fr]">
        <aside className="hidden lg:block">
          <nav className="sticky top-24 space-y-1 text-sm" aria-label="On this page">
            <p className="eyebrow mb-3">On this page</p>
            {reference.toc.map((item) => (
              <a key={item.id} href={'#' + item.id} className="block rounded-md px-2 py-1 text-mute hover:bg-ink-2 hover:text-paper">
                {item.text}
              </a>
            ))}
          </nav>
        </aside>

        <article className="min-w-0 space-y-16">
          <header>
            <p className="eyebrow">Reference</p>
            <h1 className="mt-3 font-display text-4xl font-semibold tracking-tight sm:text-5xl">
              {reference.title}
            </h1>
            <p className="mt-4 max-w-2xl text-mute">
              Settings, decorator arguments, rules and tooling at a glance. New here? Start with the{' '}
              <Link to="/" hash="quick-start" className="text-leaf-2 underline underline-offset-4">
                quick start
              </Link>
              .
            </p>
          </header>

          <div
            className="prose-reference"
            onClick={handleCopy}
            dangerouslySetInnerHTML={{ __html: reference.html }}
          />
        </article>
      </main>
      <SiteFooter />
    </>
  )
}
