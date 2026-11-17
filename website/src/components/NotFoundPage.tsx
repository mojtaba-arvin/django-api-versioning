import { Link } from '@tanstack/react-router'
import { SiteFooter, SiteHeader } from './Layout'

export function NotFoundPage() {
  return (
    <>
      <SiteHeader />
      <main className="mx-auto max-w-2xl px-5 py-32 text-center">
        <p className="font-mono text-sm text-leaf">/api/v?/this-page/</p>
        <h1 className="mt-4 font-display text-5xl font-semibold">404</h1>
        <p className="mt-4 text-mute">No version of this page has been declared.</p>
        <Link to="/" className="btn btn-primary mt-8">
          Back to home
        </Link>
      </main>
      <SiteFooter />
    </>
  )
}
