import { useMemo, useState } from 'react'
import { Link } from '@tanstack/react-router'
import type { ArticleMeta } from '../lib/articles'
import { site } from '../data/site'
import { SiteFooter, SiteHeader } from './Layout'

export function ArticlesPage({ articles }: { articles: ArticleMeta[] }) {
  const [query, setQuery] = useState('')
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return articles
    return articles.filter((a) =>
      [a.title, a.description, ...a.keywords].some((s) => s.toLowerCase().includes(q)),
    )
  }, [articles, query])

  return (
    <>
      <SiteHeader />
      <main className="mx-auto max-w-6xl px-5 py-16">
        <header className="flex flex-col gap-8 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-2xl">
            <p className="eyebrow">Articles</p>
            <h1 className="mt-3 font-display text-4xl font-semibold tracking-tight sm:text-5xl">
              Guides to versioning Django APIs
            </h1>
            <p className="mt-4 text-mute">
              {articles.length} long-form articles from the project’s{' '}
              <a href={`${site.github}/tree/main/docs/articles`} className="text-leaf-2 underline underline-offset-4">
                docs/articles
              </a>{' '}
              folder: routing models, DRF schemes, inheriting endpoints, deprecation headers and migrations.
            </p>
          </div>
          <div className="flex w-full flex-col gap-3 sm:flex-row lg:w-auto">
            <label className="relative block w-full sm:w-72">
              <span className="sr-only">Filter articles</span>
              <input
                type="search"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Filter by topic, e.g. DRF"
                className="w-full rounded-lg border border-line bg-ink-2 px-4 py-2.5 text-sm text-paper placeholder:text-mute focus:border-leaf focus:outline-none"
              />
            </label>
            <a href="/rss.xml" className="btn btn-ghost justify-center">
              <RssIcon /> RSS
            </a>
          </div>
        </header>

        {filtered.length === 0 ? (
          <p className="mt-16 text-mute">
            No articles match “{query}”.{' '}
            <button type="button" onClick={() => setQuery('')} className="text-leaf-2 underline underline-offset-4">
              Clear filter
            </button>
          </p>
        ) : (
          <ol className="mt-14 grid gap-4 md:grid-cols-2">
            {filtered.map((a) => (
              <li key={a.slug}>
                <Link
                  to="/articles/$slug"
                  params={{ slug: a.slug }}
                  className="card group flex h-full flex-col p-6 transition hover:border-leaf"
                >
                  <div className="flex items-center justify-between font-mono text-xs text-mute">
                    <span className="text-leaf">{String(a.number).padStart(3, '0')}</span>
                    <span>{a.readingMinutes} min read</span>
                  </div>
                  <h2 className="mt-3 font-display text-xl font-semibold leading-snug tracking-tight text-paper group-hover:text-leaf-2">
                    {a.title}
                  </h2>
                  <p className="mt-2 flex-1 text-sm leading-relaxed text-mute">{a.description}</p>
                  {a.keywords.length > 0 && (
                    <ul className="mt-4 flex flex-wrap gap-1.5">
                      {a.keywords.slice(0, 3).map((k) => (
                        <li key={k} className="rounded-full border border-line px-2.5 py-0.5 text-[11px] text-mute">
                          {k}
                        </li>
                      ))}
                    </ul>
                  )}
                </Link>
              </li>
            ))}
          </ol>
        )}
      </main>
      <SiteFooter />
    </>
  )
}

export function RssIcon() {
  return (
    <svg viewBox="0 0 16 16" width="14" height="14" fill="currentColor" aria-hidden>
      <path d="M2 2.5A.5.5 0 0 1 2.5 2C9.4 2 14 6.6 14 13.5a.5.5 0 0 1-.5.5h-1.5a.5.5 0 0 1-.5-.5C11.5 8 8 4.5 2.5 4.5A.5.5 0 0 1 2 4V2.5Zm0 4.5a.5.5 0 0 1 .5-.5c4 0 7 3 7 7a.5.5 0 0 1-.5.5H7.5a.5.5 0 0 1-.5-.5c0-2.5-2-4.5-4.5-4.5A.5.5 0 0 1 2 9V7Zm1.5 4a1.5 1.5 0 1 1 0 3 1.5 1.5 0 0 1 0-3Z" />
    </svg>
  )
}
