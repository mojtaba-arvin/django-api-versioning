import assert from 'node:assert/strict'
import { mkdtemp, mkdir, readFile, readdir, rm, writeFile } from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { test } from 'node:test'
import { findBrokenLocalReferences, validateDist } from './check-dist.mjs'

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url))
const canonicalDirectory = path.resolve(scriptDirectory, '../../docs/articles')
const siteOrigin = 'https://example.test'
const cacheHeaders = '/*\n  Cache-Control: public, max-age=0, must-revalidate\n\n/assets/*\n  Cache-Control: public, max-age=31536000, immutable\n'

async function canonicalSlugs() {
  const files = (await readdir(canonicalDirectory)).filter((file) => file.endsWith('.md')).sort()
  return Promise.all(files.map(async (file) => {
    const raw = await readFile(path.join(canonicalDirectory, file), 'utf8')
    const frontmatter = /^---\r?\n([\s\S]*?)\r?\n---(?:\r?\n|$)/.exec(raw)?.[1] ?? ''
    const match = /^slug:\s*(?:"([^"]+)"|'([^']+)'|([^\s#]+))\s*$/m.exec(frontmatter)
    return match?.[1] ?? match?.[2] ?? match?.[3] ?? file.replace(/\.md$/, '')
  }))
}

async function createArtifact(basePath) {
  const root = await mkdtemp(path.join(os.tmpdir(), 'website-dist-'))
  const base = basePath === '/' ? '/' : '/' + basePath.split('/').filter(Boolean).join('/') + '/'
  const slugs = await canonicalSlugs()
  const absolute = (pathname) => siteOrigin + base + pathname
  await mkdir(path.join(root, 'reference'), { recursive: true })
  await mkdir(path.join(root, 'docs'), { recursive: true })
  await mkdir(path.join(root, 'articles'), { recursive: true })
  await mkdir(path.join(root, '_build'), { recursive: true })
  await writeFile(path.join(root, '_build', 'app.js'), '/* static client asset */')
  await writeFile(path.join(root, 'favicon.svg'), '<svg></svg>')
  await writeFile(path.join(root, '_headers'), cacheHeaders)

  const html = (title, canonical, links = '', extraHead = '') =>
    '<!doctype html><html><head><title>' + title + '</title>' + extraHead +
    '<link rel="canonical" href="' + canonical + '">' +
    '<link rel="icon" type="image/svg+xml" href="' + base + 'favicon.svg"></head><body>' +
    links + '<script src="' + base + '_build/app.js"></script></body></html>'

  const homeLinks = '<a href="' + base + 'reference/">Reference</a><a href="' + base + 'articles/">Articles</a>'
  await writeFile(path.join(root, 'index.html'), html('Home', absolute(''), homeLinks))
  await writeFile(path.join(root, 'reference', 'index.html'), html('Reference', absolute('reference/'), '<a href="' + base + '">Home</a>'))
  await writeFile(
    path.join(root, 'docs', 'index.html'),
    html('Reference moved', absolute('reference/'), '<a href="' + base + 'reference/">Open Reference</a>',
      '<meta http-equiv="refresh" content="0;url=' + base + 'reference/">'),
  )
  await writeFile(path.join(root, 'articles', 'index.html'), html('Articles', absolute('articles/'), slugs.map((slug) =>
    '<a href="' + base + 'articles/' + slug + '/">' + slug + '</a>',
  ).join('')))

  for (const slug of slugs) {
    const directory = path.join(root, 'articles', slug)
    await mkdir(directory, { recursive: true })
    await writeFile(path.join(directory, 'index.html'), html(slug, absolute('articles/' + slug + '/'), '<a href="' + base + 'articles/">All articles</a>'))
  }

  const urls = [absolute(''), absolute('reference/'), absolute('articles/'), ...slugs.map((slug) => absolute('articles/' + slug + '/'))]
  const sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset>' +
    urls.map((url) => '<url><loc>' + url + '</loc></url>').join('') + '</urlset>\n'
  await writeFile(path.join(root, 'sitemap.xml'), sitemap)
  await writeFile(path.join(root, 'robots.txt'), 'User-agent: *\nAllow: ' + base + '\nSitemap: ' + absolute('sitemap.xml') + '\n')
  const redirects = [
    base + 'reference ' + base + 'reference/ 301',
    base + 'docs ' + base + 'reference/ 301',
    base + 'docs/ ' + base + 'reference/ 301',
    base + 'articles ' + base + 'articles/ 301',
    ...slugs.map((slug) => base + 'articles/' + slug + ' ' + base + 'articles/' + slug + '/ 301'),
  ].join('\n') + '\n'
  await writeFile(path.join(root, '_redirects'), redirects)

  const items = slugs.slice().reverse().map((slug) => '<item><link>' + absolute('articles/' + slug + '/')
    + '</link></item>').join('')
  await writeFile(path.join(root, 'rss.xml'), '<rss><channel>' + items + '</channel></rss>')
  return root
}

test('validates a root-hosted artifact with canonical page URLs and discovery metadata', async () => {
  const root = await createArtifact('/')
  try {
    const result = await validateDist(root, '/', siteOrigin)
    assert.equal(result.articlePages, (await canonicalSlugs()).length)
    assert.equal(result.basePath, '/')
    assert.equal(result.canonicalUrls, result.articlePages + 3)
  } finally {
    await rm(root, { recursive: true, force: true })
  }
})

test('validates a project-site artifact under /django-api-versioning/', async () => {
  const root = await createArtifact('/django-api-versioning')
  try {
    const result = await validateDist(root, '/django-api-versioning', siteOrigin)
    assert.equal(result.articlePages, (await canonicalSlugs()).length)
    assert.equal(result.basePath, '/django-api-versioning/')
  } finally {
    await rm(root, { recursive: true, force: true })
  }
})

test('rejects an unsafe project base path', async () => {
  const root = await createArtifact('/')
  try {
    await assert.rejects(() => validateDist(root, '/../outside', siteOrigin), /PUBLIC_BASE_PATH/)
  } finally {
    await rm(root, { recursive: true, force: true })
  }
})

test('rejects a static artifact without the required cache headers', async () => {
  const root = await createArtifact('/')
  try {
    await writeFile(path.join(root, '_headers'), '/*\n  Cache-Control: public, max-age=3600\n')
    await assert.rejects(() => validateDist(root, '/', siteOrigin), /cache policy must require revalidation/)
  } finally {
    await rm(root, { recursive: true, force: true })
  }
})

test('rejects an artifact whose Reference page has a non-canonical URL', async () => {
  const root = await createArtifact('/')
  try {
    const file = path.join(root, 'reference', 'index.html')
    const html = await readFile(file, 'utf8')
    await writeFile(file, html.replace('https://example.test/reference/', 'https://example.test/docs/'))
    await assert.rejects(() => validateDist(root, '/', siteOrigin), /Non-canonical or missing canonical URL/)
  } finally {
    await rm(root, { recursive: true, force: true })
  }
})

test('rejects a static artifact that omits the sitemap route', async () => {
  const root = await createArtifact('/')
  try {
    await rm(path.join(root, 'sitemap.xml'))
    await assert.rejects(() => validateDist(root, '/', siteOrigin), /Missing required static output:.*sitemap.xml/)
  } finally {
    await rm(root, { recursive: true, force: true })
  }
})

test('rejects local references that escape the configured base path', async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), 'website-links-'))
  try {
    await writeFile(path.join(root, 'index.html'), '<a href="/outside/">Outside</a>')
    const issues = await findBrokenLocalReferences(root, '/django-api-versioning')
    assert.equal(issues.length, 1)
    assert.match(issues[0], /escapes configured base path/)
  } finally {
    await rm(root, { recursive: true, force: true })
  }
})
