// Copy the canonical repository article corpus and generate static discovery metadata.
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
  if (!/^[a-z0-9-]+$/.test(slug)) throw new Error('Article slug must be lowercase URL-safe text in ' + file)
  const title = scalar(frontmatter, 'title') || /^#\s+(.+)$/m.exec(body)?.[1] || slug
  const description = scalar(frontmatter, 'description')
  const authorBlock = /^author:\s*\r?\n((?:[ \t]+.*(?:\r?\n|$))*)/m.exec(frontmatter)?.[1] ?? ''
  const author = scalar(authorBlock, 'name')
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
  if (
    (value && !value.startsWith('/')) ||
    value.startsWith('//') ||
    /[?#\\]/.test(value)
  ) {
    throw new Error('PUBLIC_BASE_PATH must be a root-relative path without query, hash, or backslashes.')
  }
  const parts = value.split('/').filter(Boolean)
  if (parts.some((part) => part === '.' || part === '..' || !/^[A-Za-z0-9._~-]+$/.test(part))) {
    throw new Error('PUBLIC_BASE_PATH contains an invalid URL path segment.')
  }
  return parts.length ? '/' + parts.join('/') + '/' : '/'
}

function normalizedOrigin(value) {
  const parsed = new URL(value)
  const isLocalHttp = parsed.protocol === 'http:' && parsed.hostname === 'localhost'
  if (
    (parsed.protocol !== 'https:' && !isLocalHttp) ||
    parsed.pathname !== '/' ||
    parsed.search ||
    parsed.hash ||
    parsed.username ||
    parsed.password
  ) {
    throw new Error('SITE_URL must be an HTTPS origin without a path, query, or credentials.')
  }
  return parsed.origin
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

const siteOrigin = normalizedOrigin(process.env.SITE_URL || 'http://localhost:3000')
const basePath = normalizedBasePath(process.env.PUBLIC_BASE_PATH)
const absolute = (pathname) => siteOrigin + basePath + pathname.replace(/^\/+/, '')
const articles = await Promise.all(entries.map(async (file) => ({
  file,
  ...articleMetadata(file, await readFile(join(source, file), 'utf8')),
})))
const slugs = articles.map((article) => article.slug)
if (new Set(slugs).size !== slugs.length) throw new Error('Article slugs must be unique')

const items = articles.slice().reverse().map((article) => {
  const link = absolute('articles/' + encodeURIComponent(article.slug) + '/')
  return [
    '<item>',
    '<title>' + xmlEscape(article.title) + '</title>',
    '<link>' + xmlEscape(link) + '</link>',
    '<guid isPermaLink="true">' + xmlEscape(link) + '</guid>',
    '<description>' + xmlEscape(article.description) + '</description>',
    article.author ? '<dc:creator>' + xmlEscape(article.author) + '</dc:creator>' : '',
    ...article.keywords.map((keyword) => '<category>' + xmlEscape(keyword) + '</category>'),
    '</item>',
  ].join('')
})

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

const sitemapUrls = [
  absolute(''),
  absolute('reference/'),
  absolute('articles/'),
  ...articles.map((article) => absolute('articles/' + encodeURIComponent(article.slug) + '/')),
]
const sitemap = [
  '<?xml version="1.0" encoding="UTF-8"?>',
  '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
  ...sitemapUrls.map((url) => '<url><loc>' + xmlEscape(url) + '</loc></url>'),
  '</urlset>',
  '',
].join('\n')

const robots = [
  'User-agent: *',
  'Allow: ' + basePath,
  'Sitemap: ' + absolute('sitemap.xml'),
  '',
].join('\n')

const redirects = [
  [basePath + 'reference', basePath + 'reference/'],
  [basePath + 'docs', basePath + 'reference/'],
  [basePath + 'docs/', basePath + 'reference/'],
  [basePath + 'articles', basePath + 'articles/'],
  ...articles.map((article) => {
    const slugPath = basePath + 'articles/' + encodeURIComponent(article.slug)
    return [slugPath, slugPath + '/']
  }),
].map(([from, to]) => from + ' ' + to + ' 301').join('\n') + '\n'

await mkdir(publicDirectory, { recursive: true })
await Promise.all([
  writeFile(join(publicDirectory, 'rss.xml'), xml, 'utf8'),
  writeFile(join(publicDirectory, 'sitemap.xml'), sitemap, 'utf8'),
  writeFile(join(publicDirectory, 'robots.txt'), robots, 'utf8'),
  writeFile(join(publicDirectory, '_redirects'), redirects, 'utf8'),
])

console.log('Synced ' + entries.length + ' canonical articles and generated RSS, sitemap, robots.txt, and redirects.')
