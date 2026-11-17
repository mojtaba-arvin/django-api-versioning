// Re-downloads the upstream articles into content/articles/.
// Usage: node scripts/sync-articles.mjs
import { mkdir, readdir, rm, writeFile } from 'node:fs/promises'
import { join } from 'node:path'

const API = 'https://api.github.com/repos/mojtaba-arvin/django-api-versioning/contents/docs/articles?ref=main'
const out = join(import.meta.dirname, '..', 'content', 'articles')

const res = await fetch(API, { headers: { accept: 'application/vnd.github+json' } })
if (!res.ok) throw new Error(`GitHub API responded ${res.status}`)
const entries = (await res.json()).filter((e) => e.type === 'file' && /^[\w.-]+\.md$/.test(e.name))

await mkdir(out, { recursive: true })
const keep = new Set(entries.map((e) => e.name))
for (const name of await readdir(out)) {
  if (name.endsWith('.md') && !keep.has(name)) await rm(join(out, name))
}
for (const e of entries) {
  const r = await fetch(e.download_url)
  if (!r.ok) throw new Error(`Failed to download ${e.name}: ${r.status}`)
  await writeFile(join(out, e.name), await r.text())
  console.log(`✓ ${e.name}`)
}
console.log(`Synced ${entries.length} articles.`)
