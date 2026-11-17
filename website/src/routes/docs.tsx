import { createFileRoute, Link } from '@tanstack/react-router'
import { SiteFooter, SiteHeader } from '../components/Layout'
import { canonicalUrl, site } from '../data/site'

const referenceTarget = `${import.meta.env.BASE_URL}reference/`

export const Route = createFileRoute('/docs')({
  component: LegacyDocsRedirect,
  head: () => ({
    meta: [
      { title: `Reference moved · ${site.name}` },
      { httpEquiv: 'refresh', content: `0;url=${referenceTarget}` },
      {
        name: 'robots',
        content: 'noindex,follow',
      },
    ],
    links: canonicalUrl('reference/')
      ? [{ rel: 'canonical', href: canonicalUrl('reference/')! }]
      : [],
  }),
})

function LegacyDocsRedirect() {
  return (
    <>
      <SiteHeader />
      <main className="mx-auto min-h-[55vh] max-w-3xl px-5 py-24">
        <p className="eyebrow">Page moved</p>
        <h1 className="mt-3 font-display text-4xl font-semibold tracking-tight">Reference has moved</h1>
        <p className="mt-4 text-mute">
          The canonical Reference page now lives at <code className="inline-code">/reference/</code>.
          You should be redirected automatically.
        </p>
        <Link to="/reference/" className="btn btn-primary mt-8">
          Open Reference
        </Link>
      </main>
      <SiteFooter />
    </>
  )
}
