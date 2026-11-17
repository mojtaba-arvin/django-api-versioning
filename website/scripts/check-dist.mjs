#!/usr/bin/env node
// Verify that the deployable artifact is a complete, host-agnostic static website.
import { access, readFile, readdir } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url))
const websiteRoot = path.resolve(scriptDirectory, '..')
const repositoryRoot = path.resolve(websiteRoot, '..')
const canonicalArticles = path.join(repositoryRoot, 'docs', 'articles')

function normalizeBasePath(value = '/') {
  const parts = value.split('/').filter(Boolean)
  return parts.length ? '/' + parts.join('/') + '/' : '/'
}

async function exists(file) {
  try { await access(file); return true } catch { return false }
}

async function walkFiles(directory, prefix = '') {
  const entries = await readdir(directory, { withFileTypes: true })
  const files = []
  for (const entry of entries) {
    const relative = path.posix.join(prefix, entry.name)
    const absolute = path.join(directory, entry.name)
    if (entry.isDirectory()) files.push(...await walkFiles(absolute, relative))
    else if (entry.isFile()) files.push(relative)
  }
  return files
}

function getSlug(file, raw) {
  const frontmatter = /^---\r?\n([\s\S]*?)\r?\n---(?:\r?\n|$)/.exec(raw)?.[1] ?? ''
  const match = /^slug:\s*(?:"([^"]+)"|'([^']+)'|([^\s#]+))\s*$/m.exec(frontmatter)
  return match?.[1] ?? match?.[2] ?? match?.[3] ?? file.replace(/\.md$/, '')
}

export async function findBrokenLocalReferences(distRoot, basePath = '/') {
  const base = normalizeBasePath(basePath)
  const pages = (await walkFiles(distRoot)).filter((file) => file.endsWith('.html'))
  const issues = []

  for (const relativePage of pages) {
    const html = await readFile(path.join(distRoot, relativePage), 'utf8')
    const attributes = html.matchAll(/\b(?:href|src)\s*=\s*(["'])(.*?)\1/gs)
    for (const match of attributes) {
      const raw = match[2].trim()
      if (!raw || /^(?:#|[a-z][a-z0-9+.-]*:|\/\/)/i.test(raw)) continue
      let url
      try {
        url = new URL(raw, 'https://static.invalid' + base + relativePage)
      } catch {
        issues.push(relativePage + ': invalid URL ' + JSON.stringify(raw))
        continue
      }
      if (url.origin !== 'https://static.invalid') continue
      let pathname
      try { pathname = decodeURIComponent(url.pathname) }
      catch {
        issues.push(relativePage + ': malformed URL encoding in ' + JSON.stringify(raw))
        continue
      }
      if (!pathname.startsWith(base)) {
        issues.push(relativePage + ': local URL escapes configured base path: ' + raw)
        continue
      }
      const relativeTarget = pathname.slice(base.length)
      const root = path.resolve(distRoot)
      const isSiteRoot = relativeTarget.length === 0
      let target = isSiteRoot
        ? path.join(root, 'index.html')
        : path.resolve(root, ...relativeTarget.split('/'))
      if (!isSiteRoot && (pathname.endsWith('/') || !path.extname(target))) {
        target = path.join(target, 'index.html')
      }
      if (target !== path.join(root, 'index.html') && !target.startsWith(root + path.sep)) {
        issues.push(relativePage + ': URL resolves outside dist: ' + raw)
      } else if (!await exists(target)) {
        issues.push(relativePage + ': missing local target for ' + raw + ' (expected ' + path.relative(root, target) + ')')
      }
    }
  }
  return issues
}

export async function validateDist(distRoot, basePath = '/') {
  const root = path.resolve(distRoot)
  const required = ['index.html', 'docs/index.html', 'articles/index.html', 'rss.xml']
  const missing = []
  for (const relative of required) {
    if (!await exists(path.join(root, relative))) missing.push(relative)
  }
  if (missing.length) throw new Error('Missing required static output: ' + missing.join(', '))

  const sourceFiles = (await readdir(canonicalArticles, { withFileTypes: true }))
    .filter((entry) => entry.isFile() && entry.name.endsWith('.md'))
    .map((entry) => entry.name)
    .sort()
  if (sourceFiles.length === 0) throw new Error('Canonical docs/articles corpus is empty')

  const expectedSlugs = await Promise.all(sourceFiles.map(async (file) =>
    getSlug(file, await readFile(path.join(canonicalArticles, file), 'utf8')),
  ))
  const missingArticles = []
  for (const slug of expectedSlugs) {
    const page = path.join(root, 'articles', slug, 'index.html')
    if (!await exists(page)) missingArticles.push(slug)
  }
  if (missingArticles.length) {
    throw new Error('Missing prerendered article pages: ' + missingArticles.join(', '))
  }

  const feed = await readFile(path.join(root, 'rss.xml'), 'utf8')
  const feedItems = [...feed.matchAll(/<item>/g)].length
  if (feedItems !== expectedSlugs.length) {
    throw new Error('RSS item count mismatch: expected ' + expectedSlugs.length + ', found ' + feedItems)
  }
  const missingFeedItems = expectedSlugs.filter((slug) =>
    !feed.includes('/articles/' + encodeURIComponent(slug) + '/'),
  )
  if (missingFeedItems.length) {
    throw new Error('RSS is missing canonical article links: ' + missingFeedItems.join(', '))
  }

  const files = await walkFiles(root)
  const forbidden = files.filter((file) =>
    /(^|\/)(?:server|functions|\.netlify|_serverFn)(?:\/|$)/i.test(file),
  )
  if (forbidden.length) {
    throw new Error('Server/runtime artifacts found in static output: ' + forbidden.join(', '))
  }
  const runtimeFiles = files.filter((file) => /\\.(?:html|js|mjs|json)$/i.test(file))
  for (const file of runtimeFiles) {
    const content = await readFile(path.join(root, file), 'utf8')
    if (content.includes('/_serverFn') || content.includes('/.netlify/functions')) {
      throw new Error('Server-function endpoint reference found in deployable file: ' + file)
    }
  }

  const broken = await findBrokenLocalReferences(root, basePath)
  if (broken.length) {
    throw new Error('Broken local references (' + broken.length + '):\n- ' + broken.join('\n- '))
  }

  const summary = {
    htmlPages: files.filter((file) => file.endsWith('.html')).length,
    articlePages: expectedSlugs.length,
    rssItems: feedItems,
    basePath: normalizeBasePath(basePath),
  }
  console.log('[static-dist] verified ' + summary.htmlPages + ' HTML pages, ' +
    summary.articlePages + ' articles, RSS, and local references at ' + summary.basePath)
  return summary
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const distRoot = process.argv[2] || path.join(websiteRoot, 'dist', 'client')
  const basePath = process.argv[3] || process.env.PUBLIC_BASE_PATH || '/'
  validateDist(distRoot, basePath).catch((error) => {
    console.error(error.message)
    process.exitCode = 1
  })
}
