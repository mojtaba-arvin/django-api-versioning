import { useState } from 'react'
import { Link } from '@tanstack/react-router'
import { site } from '../data/site'
import { caveats, features, patterns, snippets } from '../data/content'
import { CodeBlock, CopyButton } from './CodeBlock'
import { GitHubIcon, SiteFooter, SiteHeader } from './Layout'
import { Playground } from './Playground'
import { LifecycleDemo } from './LifecycleDemo'
import type { ArticleMeta } from '../lib/articles'

const STEPS = [
  { label: 'Settings', file: 'settings.py', code: snippets.settings },
  { label: 'Endpoints', file: 'billing/views.py', code: snippets.heroView },
  { label: 'URLconf', file: 'urls.py', code: snippets.urls },
]

export function HomePage({ articles = [] }: { articles?: ArticleMeta[] }) {
  return (
    <>
      <SiteHeader />
      <main>
        <Hero />
        <Features />
        <DecisionGuide />

        <QuickStart />
        <Patterns />
        <section id="playground" className="border-t border-line py-24">
          <div className="mx-auto max-w-6xl px-5">
            <SectionHead
              eyebrow="Playground"
              title="Watch declarations become a version matrix"
              body="Pick a scenario or edit the declarations. The matrix updates live using the package’s documented rules: forward segments hand over to newer ones, collisions go to the higher source version, and gaps get flagged."
            />
            <div className="mt-12">
              <Playground />
            </div>
          </div>
        </section>
        <Lifecycle />
        <Tooling />
        <GoodToKnow />
        <Articles articles={articles} />
        <Cta />
      </main>
      <SiteFooter />
    </>
  )
}

function SectionHead({ eyebrow, title, body }: { eyebrow: string; title: string; body?: string }) {
  return (
    <div className="max-w-2xl">
      <p className="eyebrow">{eyebrow}</p>
      <h2 className="section-title mt-3">{title}</h2>
      {body && <p className="mt-4 text-base leading-relaxed text-mute">{body}</p>}
    </div>
  )
}

function Hero() {
  const versions = [1, 2, 3]
  return (
    <section className="relative overflow-hidden">
      <div className="grid-bg absolute inset-0 [mask-image:linear-gradient(to_bottom,black,transparent)]" aria-hidden />
      <div className="glow absolute inset-0" aria-hidden />
      <div className="relative mx-auto grid max-w-6xl items-center gap-12 px-5 pt-20 pb-24 lg:grid-cols-[1.1fr_1fr] lg:pt-28">
        <div>
          <a
            href={site.pypi}
            className="inline-flex items-center gap-2 rounded-full border border-line bg-ink-2/80 px-3 py-1 font-mono text-xs text-mute hover:text-paper"
          >
            <span className="h-1.5 w-1.5 rounded-full bg-leaf" /> Python ≥ 3.10 · Django ≥ 4.2 · DRF optional
          </a>
          <h1 className="mt-6 font-display text-5xl leading-[1.02] font-semibold tracking-tight sm:text-6xl">
            Version your API by{' '}
            <span className="text-leaf">declaring it</span>, not copying it.
          </h1>
          <p className="mt-6 max-w-xl text-lg leading-relaxed text-mute">
            Version-aware routing for Django and DRF. Define versioned endpoints with{' '}
            <code className="inline-code">@endpoint</code>.
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-3 rounded-lg border border-line bg-ink-2 py-1.5 pr-1.5 pl-4 font-mono text-sm">
              <span className="text-leaf">$</span>
              <span>{site.install}</span>
              <CopyButton text={site.install} />
            </div>
            <a href="#quick-start" className="btn btn-primary">
              Get started
            </a>
            <a href={site.github} className="btn btn-ghost">
              <GitHubIcon /> Star on GitHub
            </a>
          </div>
        </div>

        <div className="relative">
          <CodeBlock code={snippets.heroView} title="billing/views.py" />
          <div className="card relative -mt-6 ml-6 p-4 shadow-2xl shadow-black/40 sm:ml-12">
            <p className="font-mono text-[11px] tracking-wide text-mute">GENERATED ROUTES · API_MAX_VERSION = 3</p>
            <ul className="mt-3 space-y-1.5 font-mono text-xs">
              {versions.map((v) => (
                <li key={v} className="flex items-center justify-between gap-3">
                  <span className="text-paper">/api/v{v}/invoices/&lt;id&gt;/</span>
                  {v < 2 ? (
                    <span className="rounded bg-ink-3 px-2 py-0.5 text-mute">404</span>
                  ) : (
                    <span className="rounded bg-leaf/15 px-2 py-0.5 text-leaf-2">
                      InvoiceDetailView{v > 2 && <span className="opacity-60"> ↺ v2</span>}
                    </span>
                  )}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </section>
  )
}

function Features() {
  return (
    <section id="features" className="border-t border-line py-24">
      <div className="mx-auto max-w-6xl px-5">
        <SectionHead
          eyebrow="Why"
          title="One source of truth for every API version"
          body="Stop duplicating URLconfs and view modules for each release. Declare where an implementation starts, and let the router fill in the rest."
        />
        <div className="mt-12 grid gap-px overflow-hidden rounded-2xl border border-line bg-line sm:grid-cols-2 lg:grid-cols-3">
          {features.map((f) => (
            <div key={f.title} className="bg-ink-2 p-6 transition hover:bg-ink-3">
              <span className="grid h-10 w-10 place-items-center rounded-lg border border-line font-mono text-leaf">
                {f.icon}
              </span>
              <h3 className="mt-5 font-display text-lg font-semibold">{f.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-mute">{f.body}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

function DecisionGuide() {
  return (
    <section id="decision-guide" className="border-t border-line py-20">
      <div className="mx-auto max-w-6xl px-5">
        <SectionHead
          eyebrow="Choose the right tool"
          title="Is declarative versioned routing right for your API?"
          body="The package is focused on one job: selecting the correct endpoint implementation for each API version while carrying unchanged routes forward."
        />
        <div className="mt-10 grid gap-4 lg:grid-cols-2">
          <div className="card p-6">
            <h3 className="font-semibold text-leaf-2">A good fit when you need to</h3>
            <ul className="mt-4 space-y-3 text-sm leading-relaxed text-mute">
              <li>• Change only selected endpoints between API versions without cloning every URL pattern.</li>
              <li>• Keep version-to-view ownership explicit for Django views or DRF ViewSets.</li>
              <li>• Inspect and regression-test the effective route matrix as the API evolves.</li>
              <li>• Introduce versioned routing incrementally while keeping application business logic in your views.</li>
            </ul>
          </div>
          <div className="card p-6">
            <h3 className="font-semibold">You may not need it when</h3>
            <ul className="mt-4 space-y-3 text-sm leading-relaxed text-mute">
              <li>• DRF's built-in versioning already solves your only requirement: identifying the requested version.</li>
              <li>• Your main need is serializer or response transformation, tenant-specific version policy, or automatic semantic compatibility.</li>
              <li>• You intentionally want to maintain a separate URL configuration for every API version.</li>
            </ul>
          </div>
        </div>
        <p className="mt-6 max-w-3xl text-sm leading-relaxed text-mute">
          Django REST Framework is optional for Django-native endpoints. The package manages route registration and view selection; your project remains responsible for response contracts, authorization, and business-level compatibility. See the <Link to="/reference/" className="text-leaf-2 underline underline-offset-4 hover:text-leaf">reference</Link> for exact boundaries.
        </p>
      </div>
    </section>
  )
}

function QuickStart() {
  const [step, setStep] = useState(0)
  return (
    <section id="quick-start" className="border-t border-line py-24">
      <div className="mx-auto grid max-w-6xl gap-12 px-5 lg:grid-cols-[0.9fr_1.1fr]">
        <div>
          <SectionHead eyebrow="Quick start" title="Three steps to versioned routes" />
          <ol className="mt-10 space-y-3">
            {STEPS.map((s, i) => (
              <li key={s.label}>
                <button
                  type="button"
                  onClick={() => setStep(i)}
                  aria-pressed={step === i}
                  className={`flex w-full items-start gap-4 rounded-xl border p-4 text-left transition ${
                    step === i ? 'border-leaf bg-leaf/10' : 'border-line hover:border-mute/50'
                  }`}
                >
                  <span
                    className={`grid h-8 w-8 shrink-0 place-items-center rounded-full font-mono text-sm ${
                      step === i ? 'bg-leaf text-ink' : 'bg-ink-3 text-mute'
                    }`}
                  >
                    {i + 1}
                  </span>
                  <span>
                    <span className="block font-semibold">{s.label}</span>
                    <span className="mt-1 block text-sm text-mute">
                      {i === 0 && 'Add the app and set your base path and version bounds.'}
                      {i === 1 && 'Decorate views with @endpoint and a starting version.'}
                      {i === 2 && 'Import endpoint modules first, then include the generated patterns.'}
                    </span>
                  </span>
                </button>
              </li>
            ))}
          </ol>
          <p className="mt-6 text-sm text-mute">
            Result: <code className="inline-code">/api/v1/invoices/42/</code> returns 404, while v2 and v3 are both
            served by <code className="inline-code">InvoiceDetailView</code>.
          </p>
        </div>
        <div className="lg:pt-16">
          <CodeBlock key={step} code={STEPS[step].code} title={STEPS[step].file} />
        </div>
      </div>
    </section>
  )
}

function Patterns() {
  const max = 5
  return (
    <section className="border-t border-line py-24">
      <div className="mx-auto max-w-6xl px-5">
        <SectionHead
          eyebrow="Registration patterns"
          title="Four ways to say which versions a view serves"
          body={`Shown with API_MAX_VERSION = ${max}. Combining version and versions raises VersionRangeError.`}
        />
        <div className="mt-12 card divide-y divide-line">
          {patterns.map((p) => (
            <div key={p.name} className="grid items-center gap-4 p-5 md:grid-cols-[180px_1fr_auto]">
              <div>
                <p className="font-semibold">{p.name}</p>
                <p className="font-mono text-xs text-mute">{p.result}</p>
              </div>
              <code className="overflow-x-auto font-mono text-sm text-leaf-2">{p.code}</code>
              <div className="flex gap-1.5" aria-label={`Serves ${p.result}`}>
                {p.on.length === 0 ? (
                  <span className="rounded-md border border-dashed border-line px-3 py-1 font-mono text-xs text-mute">
                    no version prefix
                  </span>
                ) : (
                  Array.from({ length: max }, (_, i) => i + 1).map((v) => (
                    <span
                      key={v}
                      className={`grid h-8 w-9 place-items-center rounded-md font-mono text-xs ${
                        p.on.includes(v) ? 'bg-leaf text-ink font-semibold' : 'border border-line text-mute/60'
                      }`}
                    >
                      v{v}
                    </span>
                  ))
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

function Lifecycle() {
  return (
    <section id="lifecycle" className="border-t border-line py-24">
      <div className="mx-auto grid max-w-6xl gap-12 px-5 lg:grid-cols-2">
        <div>
          <SectionHead
            eyebrow="Lifecycle"
            title="Deprecate and sunset versions over HTTP"
            body="LifecycleMiddleware tells clients what’s coming. Deprecated versions get an RFC 9745 Deprecation header and an RFC 8594 Sunset header; once the sunset date passes, requests receive 410 Gone."
          />
          <CodeBlock className="mt-8" code={snippets.lifecycle} title="settings.py" />
        </div>
        <div className="lg:pt-24">
          <p className="mb-3 text-sm text-mute">Try a request against each version:</p>
          <LifecycleDemo />
          <p className="mt-4 text-xs text-mute">
            Deprecated entries require a valid <code className="inline-code">deprecated_at</code>. The middleware reads
            its settings on every request. Version 1.2.0 also adds operation-scoped lifecycle declarations
            for decorator endpoints and VersionedRouter actions, with optional OpenAPI deprecation metadata. Endpoint-level
            Sunset remains headers-only; it does not retire the route or return 410.
          </p>
        </div>
      </div>
    </section>
  )
}

function Tooling() {
  return (
    <section className="border-t border-line py-24">
      <div className="mx-auto max-w-6xl px-5">
        <SectionHead
          eyebrow="Reliability"
          title="Know exactly what each version serves"
          body="Versioning bugs are silent: a route disappears from v4 and nobody notices until a client breaks. These tools make the matrix visible and testable."
        />
        <div className="mt-12 grid gap-6 lg:grid-cols-3">
          <ToolCard title="check_versions" body="Prints the route matrix grouped by logical endpoint and warns about gaps.">
            <CodeBlock code={snippets.checkVersions} lang="bash" title="terminal" />
          </ToolCard>
          <ToolCard title="assert_version_matrix" body="Snapshot the matrix in CI and fail with a diff on unexpected changes.">
            <CodeBlock code={snippets.snapshot} title="tests/test_routes.py" />
          </ToolCard>
          <ToolCard title="api_reverse" body="Reverse a named route for a specific version.">
            <CodeBlock code={snippets.reverse} title="anywhere.py" />
          </ToolCard>
        </div>
      </div>
    </section>
  )
}

function ToolCard({ title, body, children }: { title: string; body: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-4">
      <div>
        <h3 className="font-mono text-base font-semibold text-leaf-2">{title}</h3>
        <p className="mt-1 text-sm text-mute">{body}</p>
      </div>
      {children}
    </div>
  )
}

function GoodToKnow() {
  return (
    <section className="border-t border-line py-24">
      <div className="mx-auto max-w-6xl px-5">
        <SectionHead eyebrow="Good to know" title="Before you ship" />
        <div className="mt-10 grid gap-4 sm:grid-cols-2">
          {caveats.map((c) => (
            <div key={c.title} className="card p-5">
              <h3 className="font-semibold">{c.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-mute">{c.body}</p>
            </div>
          ))}
        </div>
        <p className="mt-8 text-sm text-mute">
          Full settings, arguments, and collision rules are on the{' '}
          <Link to="/reference/" className="text-leaf-2 underline underline-offset-4 hover:text-leaf">
            reference page
          </Link>
          .
        </p>
      </div>
    </section>
  )
}

const FEATURED_ARTICLES = [
  '022-what-is-django-api-versioning',
  '007-inherit-unchanged-endpoints-between-versions',
  '018-deprecate-django-api-versioning-routes-sunset-headers',
]

function Articles({ articles }: { articles: ArticleMeta[] }) {
  const featured = FEATURED_ARTICLES.map((slug) => articles.find((a) => a.slug === slug)).filter(
    (a): a is ArticleMeta => Boolean(a),
  )
  if (featured.length === 0) return null
  return (
    <section id="articles" className="border-t border-line py-24">
      <div className="mx-auto max-w-6xl px-5">
        <div className="flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between">
          <SectionHead
            eyebrow="Articles"
            title="Go deeper"
            body={`${articles.length} long-form guides on routing models, inheriting endpoints, deprecation and migrations.`}
          />
          <Link to="/articles/" className="btn btn-ghost shrink-0 self-start sm:self-auto">
            All articles →
          </Link>
        </div>
        <div className="mt-12 grid gap-4 md:grid-cols-3">
          {featured.map((a) => (
            <Link
              key={a.slug}
              to="/articles/$slug/"
              params={{ slug: a.slug }}
              className="card group flex flex-col p-6 transition hover:border-leaf"
            >
              <span className="font-mono text-xs text-mute">{a.readingMinutes} min read</span>
              <h3 className="mt-3 font-display text-lg font-semibold leading-snug text-paper group-hover:text-leaf-2">
                {a.title}
              </h3>
              <p className="mt-2 text-sm leading-relaxed text-mute">{a.description}</p>
            </Link>
          ))}
        </div>
      </div>
    </section>
  )
}

function Cta() {
  return (
    <section className="border-t border-line">
      <div className="relative mx-auto max-w-6xl overflow-hidden px-5 py-24 text-center">
        <div className="glow absolute inset-0" aria-hidden />
        <h2 className="relative font-display text-4xl font-semibold tracking-tight sm:text-5xl">
          Ship v2 without copying v1.
        </h2>
        <p className="relative mx-auto mt-4 max-w-xl text-mute">
          Open source and MIT licensed. Tested in CI against Django 4.2, 5.2, 6.0 and 6.1.
        </p>
        <div className="relative mt-8 flex flex-wrap justify-center gap-3">
          <a href={site.pypi} className="btn btn-primary">
            Install from PyPI
          </a>
          <a href={site.github} className="btn btn-ghost">
            <GitHubIcon /> View source
          </a>
        </div>
      </div>
    </section>
  )
}
