import type { MouseEvent } from 'react'
import { Link } from '@tanstack/react-router'
import type { ArticleWithNeighbours } from '../server/articles'
import { SiteFooter, SiteHeader } from './Layout'

/** Delegated handler for the copy buttons rendered into article code blocks. */
function handleCopy(e: MouseEvent<HTMLElement>) {
  const btn = (e.target as HTMLElement).closest<HTMLButtonElement>('button[data-copy]')
  if (!btn) return
  const code = btn.closest('figure')?.querySelector('pre')?.textContent ?? ''
  navigator.clipboard?.writeText(code).then(() => {
    btn.textContent = 'Copied ✓'
    setTimeout(() => {
      btn.textContent = 'Copy'
    }, 1600)
  })
}

export function ArticlePage({ article }: { article: ArticleWithNeighbours }) {
  const { prev, next } = article
  return (
    <>
      <SiteHeader />
      <main className="mx-auto grid max-w-6xl gap-12 px-5 py-16 lg:grid-cols-[220px_minmax(0,1fr)]">
        <aside className="hidden lg:block">
          <nav className="sticky top-24 max-h-[calc(100vh-7rem)] space-y-1 overflow-y-auto text-sm" aria-label="On this page">
            <Link to="/articles" className="mb-6 block font-mono text-xs text-mute hover:text-leaf-2">
              ← All articles
            </Link>
            {article.toc.length > 0 && <p className="eyebrow mb-3">On this page</p>}
            {article.toc.map((t) => (
              <a
                key={t.id}
                href={`#${t.id}`}
                className="block rounded-md px-2 py-1 leading-snug text-mute hover:bg-ink-2 hover:text-paper"
              >
                {t.text}
              </a>
            ))}
          </nav>
        </aside>

        <article className="min-w-0 max-w-3xl">
          <header className="border-b border-line pb-8">
            <Link to="/articles" className="eyebrow hover:text-leaf-2 lg:hidden">
              ← Articles
            </Link>
            <p className="eyebrow mt-4 lg:mt-0">Article {String(article.number).padStart(3, '0')}</p>
            <h1 className="mt-3 font-display text-4xl font-semibold leading-tight tracking-tight sm:text-5xl">
              {article.title}
            </h1>
            {article.description && <p className="mt-4 text-lg leading-relaxed text-mute">{article.description}</p>}
            <div className="mt-6 flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-mute">
              <span>
                By{' '}
                {article.author.url ? (
                  <a href={article.author.url} rel="noopener noreferrer" className="text-paper hover:text-leaf-2">
                    {article.author.name}
                  </a>
                ) : (
                  <span className="text-paper">{article.author.name}</span>
                )}
              </span>
              <span aria-hidden>·</span>
              <span>{article.readingMinutes} min read</span>
              <span aria-hidden>·</span>
              <a href={article.sourceUrl} className="hover:text-leaf-2">
                View source on GitHub
              </a>
            </div>
          </header>

          <div
            className="prose-article mt-10"
            onClick={handleCopy}
            dangerouslySetInnerHTML={{ __html: article.html }}
          />

          <nav className="mt-16 grid gap-4 border-t border-line pt-8 sm:grid-cols-2" aria-label="More articles">
            {prev ? (
              <Link to="/articles/$slug" params={{ slug: prev.slug }} className="card p-5 transition hover:border-leaf">
                <span className="font-mono text-xs text-mute">← Previous</span>
                <span className="mt-1 block font-display font-semibold text-paper">{prev.title}</span>
              </Link>
            ) : (
              <span />
            )}
            {next && (
              <Link
                to="/articles/$slug"
                params={{ slug: next.slug }}
                className="card p-5 text-right transition hover:border-leaf"
              >
                <span className="font-mono text-xs text-mute">Next →</span>
                <span className="mt-1 block font-display font-semibold text-paper">{next.title}</span>
              </Link>
            )}
          </nav>
        </article>
      </main>
      <SiteFooter />
    </>
  )
}
