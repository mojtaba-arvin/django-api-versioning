import { Link } from '@tanstack/react-router'
import { nav, rssHref, site } from '../data/site'

export function Logo() {
  return (
    <span className="flex items-center gap-2.5">
      <span
        aria-hidden
        className="grid h-8 w-9 place-items-center rounded-lg bg-leaf font-mono text-xs font-bold text-ink"
      >
        {'{v}'}
      </span>
      <span className="font-mono text-sm font-semibold tracking-tight text-paper">
        django-api-versioning
      </span>
    </span>
  )
}

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-40 border-b border-line/70 bg-ink/80 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-5">
        <Link to="/" aria-label="django-api-versioning home">
          <Logo />
        </Link>
        <nav className="hidden items-center gap-6 text-sm text-mute md:flex">
          {nav.map((n) => (
            <a key={n.href} href={n.href} className="hover:text-paper">
              {n.label}
            </a>
          ))}
          <Link
            to="/docs"
            className="hover:text-paper"
            activeProps={{ className: 'text-paper' }}
          >
            Reference
          </Link>
          <Link
            to="/articles"
            className="hover:text-paper"
            activeProps={{ className: 'text-paper' }}
          >
            Articles
          </Link>
        </nav>
        <div className="flex items-center gap-2">
          <a href={site.pypi} className="btn btn-ghost hidden !px-3 !py-1.5 sm:inline-flex">
            PyPI
          </a>
          <a href={site.github} className="btn btn-primary !px-3 !py-1.5">
            <GitHubIcon /> GitHub
          </a>
        </div>
      </div>
    </header>
  )
}

export function SiteFooter() {
  return (
    <footer className="border-t border-line">
      <div className="mx-auto flex max-w-6xl flex-col gap-6 px-5 py-10 text-sm text-mute sm:flex-row sm:items-center sm:justify-between">
        <div className="space-y-2">
          <Logo />
          <p>
            Built by {site.author}. Released under the {site.license} License.
          </p>
        </div>
        <div className="flex flex-wrap gap-5">
          <Link to="/docs" className="hover:text-paper">
            Reference
          </Link>
          <Link to="/articles" className="hover:text-paper">
            Articles
          </Link>
          <a href={rssHref} className="hover:text-paper">
            RSS
          </a>
          <a href={site.github} className="hover:text-paper">
            Source
          </a>
          <a href={`${site.github}/issues`} className="hover:text-paper">
            Issues
          </a>
          <a href={site.pypi} className="hover:text-paper">
            PyPI
          </a>
        </div>
      </div>
    </footer>
  )
}

export function GitHubIcon() {
  return (
    <svg viewBox="0 0 16 16" width="16" height="16" fill="currentColor" aria-hidden>
      <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z" />
    </svg>
  )
}
