import assert from 'node:assert/strict'
import { mkdtemp, mkdir, readFile, readdir, rm, writeFile } from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { test } from 'node:test'
import { findBrokenLocalReferences, validateDist } from './check-dist.mjs'

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url))
const canonicalDirectory = path.resolve(scriptDirectory, '../../docs/articles')

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
  await mkdir(path.join(root, 'docs'), { recursive: true })
  await mkdir(path.join(root, 'articles'), { recursive: true })
  await mkdir(path.join(root, '_build'), { recursive: true })
  await writeFile(path.join(root, '_build', 'app.js'), '/* static client asset */')
  await writeFile(path.join(root, 'favicon.svg'), '<svg></svg>')
  const html = (title, links = '') =>
    '<!doctype html><html><head><title>' + title + '</title><link rel="icon" type="image/svg+xml" href="' + base + 'favicon.svg"></head><body>' + links +
    '<script src="' + base + '_build/app.js"></script></body></html>'
  const links = '<a href="' + base + 'docs/">Reference</a><a href="' + base + 'articles/">Articles</a>'
  await writeFile(path.join(root, 'index.html'), html('Home', links))
  await writeFile(path.join(root, 'docs', 'index.html'), html('Reference', '<a href="' + base + '">Home</a>'))
  await writeFile(path.join(root, 'articles', 'index.html'), html('Articles', slugs.map((slug) =>
    '<a href="' + base + 'articles/' + slug + '/">' + slug + '</a>',
  ).join('')))
  for (const slug of slugs) {
    const directory = path.join(root, 'articles', slug)
    await mkdir(directory, { recursive: true })
    await writeFile(path.join(directory, 'index.html'), html(slug, '<a href="' + base + 'articles/">All articles</a>'))
  }
  const items = slugs.map((slug) => '<item><link>https://example.test' + base + 'articles/' + slug + '/</link></item>').join('')
  await writeFile(path.join(root, 'rss.xml'), '<rss><channel>' + items + '</channel></rss>')
  return root
}

test('validates a root-hosted static artifact', async () => {
  const root = await createArtifact('/')
  try {
    const result = await validateDist(root, '/')
    assert.equal(result.articlePages, (await canonicalSlugs()).length)
    assert.equal(result.basePath, '/')
  } finally {
    await rm(root, { recursive: true, force: true })
  }
})

test('validates a project-site artifact under /django-api-versioning/', async () => {
  const root = await createArtifact('/django-api-versioning')
  try {
    const result = await validateDist(root, '/django-api-versioning')
    assert.equal(result.articlePages, (await canonicalSlugs()).length)
    assert.equal(result.basePath, '/django-api-versioning/')
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
