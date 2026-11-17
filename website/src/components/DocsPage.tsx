import { Link } from '@tanstack/react-router'
import { snippets } from '../data/content'
import { CodeBlock } from './CodeBlock'
import { SiteFooter, SiteHeader } from './Layout'

const SETTINGS = [
  ['API_BASE_PATH', '"api/v{version}/"', 'URL prefix for versioned routes. Must contain exactly one plain {version} field.'],
  ['API_MIN_VERSION', '1', 'Lowest version served. Declarations below it are skipped with a warning.'],
  ['API_MAX_VERSION', '1', 'Highest version served. Declarations above it raise InvalidVersionError.'],
  ['API_VERSION_LIFECYCLE', '{}', 'Per-version status, deprecated_at and sunset used by LifecycleMiddleware.'],
  ['API_VERSIONING_CHANNELS', '["path"]', 'Validated, but not used for routing.'],
  ['API_EFFECTIVE_VERSION_RESOLVER', 'None', 'Validated, but not used for routing.'],
]

const ARGS = [
  ['postfix', 'required', 'Resource path, positional. e.g. "invoices/<int:invoice_id>/"'],
  ['version', 'None', 'Start of a forward segment.'],
  ['versions', 'None', 'Explicit list of versions, or ver_range(a, b).'],
  ['app_name', 'None', 'Optional grouping segment.'],
  ['view_name', 'None', 'Name used by api_reverse().'],
]

const ERRORS = [
  ['VersionRangeError', 'Both version and versions were passed to @endpoint.'],
  ['InvalidVersionError', 'A declared version is above API_MAX_VERSION.'],
  ['AmbiguousVersionError', 'api_reverse() was called without a version and several routes match.'],
  ['VersionMatrixError', 'assert_version_matrix() found a difference from the snapshot.'],
]

const TOC = [
  ['install', 'Installation'],
  ['settings', 'Settings'],
  ['endpoint', '@endpoint arguments'],
  ['rules', 'Validation & collisions'],
  ['errors', 'Exceptions'],
  ['commands', 'Management commands'],
  ['development', 'Development'],
]

export function DocsPage() {
  return (
    <>
      <SiteHeader />
      <main className="mx-auto grid max-w-6xl gap-12 px-5 py-16 lg:grid-cols-[200px_1fr]">
        <aside className="hidden lg:block">
          <nav className="sticky top-24 space-y-1 text-sm" aria-label="On this page">
            <p className="eyebrow mb-3">On this page</p>
            {TOC.map(([id, label]) => (
              <a key={id} href={`#${id}`} className="block rounded-md px-2 py-1 text-mute hover:bg-ink-2 hover:text-paper">
                {label}
              </a>
            ))}
          </nav>
        </aside>

        <article className="min-w-0 space-y-16">
          <header>
            <p className="eyebrow">Reference</p>
            <h1 className="mt-3 font-display text-4xl font-semibold tracking-tight sm:text-5xl">
              django-api-versioning reference
            </h1>
            <p className="mt-4 max-w-2xl text-mute">
              Settings, decorator arguments, rules and tooling at a glance. New here? Start with the{' '}
              <Link to="/" hash="quick-start" className="text-leaf-2 underline underline-offset-4">
                quick start
              </Link>
              .
            </p>
          </header>

          <Section id="install" title="Installation">
            <CodeBlock code="$ pip install django-api-versioning" lang="bash" title="terminal" />
            <p className="text-mute">
              Requires Python ≥ 3.10 and Django ≥ 4.2. Django REST Framework is optional. CI covers Django 4.2, 5.2,
              6.0 and 6.1 (5.0 and 5.1 are not covered).
            </p>
          </Section>

          <Section id="settings" title="Settings">
            <Table head={['Setting', 'Default', 'Description']} rows={SETTINGS} />
          </Section>

          <Section id="endpoint" title="@endpoint arguments">
            <Table head={['Argument', 'Default', 'Purpose']} rows={ARGS} />
            <CodeBlock
              title="views.py"
              code={`from django_api_versioning import endpoint, ver_range

@endpoint("reports/", version=3)                      # v3 → max
@endpoint("ranking/", versions=[2, 4])                # v2 and v4 only
@endpoint("legacy/", versions=ver_range(1, 3))        # v1, v2, v3
@endpoint("health/")                                  # unversioned: /health/`}
            />
            <p className="text-sm text-mute">
              Each line above is a separate example. When a route has several forward declarations (for example{' '}
              <code className="inline-code">version=1</code> and <code className="inline-code">version=3</code>), each
              serves from its own version until the next declaration takes over.
            </p>
          </Section>

          <Section id="rules" title="Validation & collisions">
            <ul className="list-disc space-y-2 pl-5 text-mute marker:text-leaf">
              <li>Combining <code className="inline-code">version</code> and <code className="inline-code">versions</code> raises <code className="inline-code">VersionRangeError</code>.</li>
              <li>A version above the maximum raises <code className="inline-code">InvalidVersionError</code>.</li>
              <li>Versions below the minimum trigger a warning and are skipped.</li>
              <li>Booleans are rejected as version values.</li>
              <li>On collision the higher <code className="inline-code">source_version</code> wins.</li>
              <li>If source versions are equal, or either is <code className="inline-code">None</code>, the last registration wins.</li>
              <li>The package does not set <code className="inline-code">request.version</code>; configure DRF versioning separately if you need it.</li>
              <li>Route settings are read at import time, so <code className="inline-code">override_settings</code> won’t rebuild URL patterns.</li>
              <li>ViewSets need a pre-configured callable, e.g. <code className="inline-code">MyViewSet.as_view({'{'}"get": "list"{'}'})(request)</code>.</li>
            </ul>
          </Section>

          <Section id="errors" title="Exceptions">
            <Table head={['Exception', 'Raised when']} rows={ERRORS} />
          </Section>

          <Section id="commands" title="Management commands">
            <CodeBlock code={snippets.checkVersions} lang="bash" title="check_versions" />
            <p className="text-mute">
              Upgrading from 0.2.0, which used <code className="inline-code">forward</code>/
              <code className="inline-code">backward</code> flags? Preview the rewrite and review every change:
            </p>
            <CodeBlock code={snippets.migrate} lang="bash" title="migrate_endpoints" />
          </Section>

          <Section id="development" title="Development">
            <CodeBlock code={snippets.dev} lang="bash" title="terminal" />
            <p className="text-mute">
              Contributions are welcome on{' '}
              <a href="https://github.com/mojtaba-arvin/django-api-versioning" className="text-leaf-2 underline underline-offset-4">
                GitHub
              </a>
              . The full README there is the canonical documentation.
            </p>
          </Section>
        </article>
      </main>
      <SiteFooter />
    </>
  )
}

function Section({ id, title, children }: { id: string; title: string; children: React.ReactNode }) {
  return (
    <section id={id} className="space-y-5">
      <h2 className="font-display text-2xl font-semibold tracking-tight">
        <a href={`#${id}`} className="group">
          {title} <span className="text-line group-hover:text-leaf">#</span>
        </a>
      </h2>
      {children}
    </section>
  )
}

function Table({ head, rows }: { head: string[]; rows: string[][] }) {
  return (
    <div className="card overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead className="border-b border-line bg-ink-3/60 text-xs uppercase tracking-wider text-mute">
          <tr>
            {head.map((h) => (
              <th key={h} className="px-4 py-3 font-medium">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {rows.map((r) => (
            <tr key={r[0]}>
              {r.map((c, i) => (
                <td key={i} className={`px-4 py-3 align-top ${i === 0 ? 'font-mono text-leaf-2 whitespace-nowrap' : i === 1 && r.length === 3 ? 'font-mono text-paper whitespace-nowrap' : 'text-mute'}`}>
                  {c}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
