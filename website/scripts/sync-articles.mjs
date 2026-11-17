// Copy the canonical repository article corpus and generate the static RSS feed.
// Usage: pnpm run sync:articles
import { copyFile, mkdir, readdir, readFile, rm, writeFile } from 'node:fs/promises'
import { join } from 'node:path'

const websiteRoot = join(import.meta.dirname, '..')
const repositoryRoot = join(websiteRoot, '..')
const source = join(repositoryRoot, 'docs', 'articles')
const output = join(websiteRoot, 'content', 'articles')
const publicDirectory = join(websiteRoot, 'public')

function xmlEscape(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&apos;')
}

function scalar(frontmatter, key) {
  const match = new RegExp('^' + key + ':\\s*(.*)$', 'm').exec(frontmatter)
  if (!match) return ''
  const value = match[1].trim()
  if (value.startsWith('"') && value.endsWith('"')) {
    try { return JSON.parse(value) } catch { return value.slice(1, -1) }
  }
  if (value.startsWith("'") && value.endsWith("'")) return value.slice(1, -1).replaceAll("''", "'")
  return value
}

function articleMetadata(file, raw) {
  const match = /^---\r?\n([\s\S]*?)\r?\n---(?:\r?\n|$)/.exec(raw)
  if (!match) throw new Error('Missing front matter in ' + file)
  const frontmatter = match[1]
  const body = raw.slice(match[0].length)
  const slug = scalar(frontmatter, 'slug') || file.replace(/\.md$/, '')
  const title = scalar(frontmatter, 'title') || /^#\s+(.+)$/m.exec(body)?.[1] || slug
  const description = scalar(frontmatter, 'description')
  const authorBlock = /^author:\s*\r?\n((?:[ \t]+.*(?:\r?\n|$))*)/m.exec(frontmatter)?.[1] ?? ''
  const author = /^\s+name:\s*(.+)$/m.exec(authorBlock)?.[1] ?? ''
  const keywordsBlock = /^keywords:\s*\r?\n((?:[ \t]+-\s+.*(?:\r?\n|$))*)/m.exec(frontmatter)?.[1] ?? ''
  const keywords = [...keywordsBlock.matchAll(/^\s+-\s+(.+)$/gm)].map((item) => {
    const value = item[1].trim()
    if (value.startsWith('"') && value.endsWith('"')) {
      try { return JSON.parse(value) } catch { return value.slice(1, -1) }
    }
    if (value.startsWith("'") && value.endsWith("'")) return value.slice(1, -1).replaceAll("''", "'")
    return value
  })
  return { slug, title, description, author, keywords }
}

function normalizedBasePath(value = '/') {
  const parts = value.split('/').filter(Boolean)
  return parts.length ? '/' + parts.join('/') + '/' : '/'
}

const entries = (await readdir(source, { withFileTypes: true }))
  .filter((entry) => entry.isFile() && /^[\w.-]+\.md$/.test(entry.name))
  .map((entry) => entry.name)
  .sort()

if (entries.length === 0) {
  throw new Error('No Markdown articles found in canonical source: ' + source)
}

await mkdir(output, { recursive: true })
const expected = new Set(entries)
for (const name of await readdir(output)) {
  if (name.endsWith('.md') && !expected.has(name)) await rm(join(output, name))
}
for (const name of entries) await copyFile(join(source, name), join(output, name))

const baseUrl = (process.env.SITE_URL || process.env.URL || 'http://localhost:3000').replace(/\/+$/, '')
const basePath = normalizedBasePath(process.env.PUBLIC_BASE_PATH)
const absolute = (path) => baseUrl + basePath + path.replace(/^\/+/, '')
const items = await Promise.all(entries.map(async (file) => {
  const metadata = articleMetadata(file, await readFile(join(source, file), 'utf8'))
  const link = absolute('articles/' + encodeURIComponent(metadata.slug) + '/')
  return [
    '<item>',
    '<title>' + xmlEscape(metadata.title) + '</title>',
    '<link>' + xmlEscape(link) + '</link>',
    '<guid isPermaLink="true">' + xmlEscape(link) + '</guid>',
    '<description>' + xmlEscape(metadata.description) + '</description>',
    metadata.author ? '<dc:creator>' + xmlEscape(metadata.author) + '</dc:creator>' : '',
    ...metadata.keywords.map((keyword) => '<category>' + xmlEscape(keyword) + '</category>'),
    '</item>',
  ].join('')
}))

const feed = absolute('rss.xml')
const xml = [
  '<?xml version="1.0" encoding="UTF-8"?>',
  '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom" xmlns:dc="http://purl.org/dc/elements/1.1/">',
  '<channel>',
  '<title>django-api-versioning articles</title>',
  '<link>' + xmlEscape(absolute('articles/')) + '</link>',
  '<atom:link href="' + xmlEscape(feed) + '" rel="self" type="application/rss+xml" />',
  '<description>Guides on Django and DRF API versioning from the django-api-versioning project.</description>',
  '<language>en</language>',
  ...items,
  '</channel>',
  '</rss>',
  '',
].join('\n')
await mkdir(publicDirectory, { recursive: true })
await writeFile(join(publicDirectory, 'rss.xml'), xml, 'utf8')

console.log('Synced ' + entries.length + ' canonical articles and generated public/rss.xml.')
