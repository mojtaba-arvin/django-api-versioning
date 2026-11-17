#!/usr/bin/env node
// Verify the deployable artifact is a complete, canonical, host-agnostic static website.
import { access, readFile, readdir } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url))
const websiteRoot = path.resolve(scriptDirectory, '..')
const repositoryRoot = path.resolve(websiteRoot, '..')
const canonicalArticles = path.join(repositoryRoot, 'docs', 'articles')

function normalizeBasePath(value = '/') {
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

function normalizeSiteOrigin(value) {
  if (!value) throw new Error('SITE_URL is required to validate canonical URLs in a production artifact')
  const parsed = new URL(value)
  if (
    parsed.protocol !== 'https:' ||
    parsed.pathname !== '/' ||
    parsed.search ||
    parsed.hash ||
    parsed.username ||
    parsed.password
  ) throw new Error('SITE_URL must be an HTTPS origin without a path, query, or credentials')
  return parsed.origin
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

function canonicalHref(html) {
  const match = html.match(/<link\b(?=[^>]*\brel=["']canonical["'])(?=[^>]*\bhref=["']([^"']+)["'])[^>]*>/i)
  return match?.[1] ?? null
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

export async function validateDist(distRoot, basePath = '/', siteUrl = process.env.SITE_URL) {
  const root = path.resolve(distRoot)
  const base = normalizeBasePath(basePath)
  const origin = normalizeSiteOrigin(siteUrl)
  const absolute = (pathname) => origin + base + pathname.replace(/^\/+/, '')
  const required = [
    'index.html',
    'reference/index.html',
    'docs/index.html',
    'articles/index.html',
    'rss.xml',
    'sitemap.xml',
    'robots.txt',
    '_redirects',
    'favicon.svg',
    '_headers',
  ]
  const missing = []
  for (const relative of required) {
    if (!await exists(path.join(root, relative))) missing.push(relative)
  }
  if (missing.length) throw new Error('Missing required static output: ' + missing.join(', '))

  const cacheHeaders = await readFile(path.join(root, '_headers'), 'utf8')
  if (!/^\/\*\s*\r?\n\s+Cache-Control:\s*public,\s*max-age=0,\s*must-revalidate\s*$/m.test(cacheHeaders)) {
    throw new Error('Static cache policy must require revalidation for HTML and unhashed public files')
  }
  if (!/^\/assets\/\*\s*\r?\n\s+Cache-Control:\s*public,\s*max-age=31536000,\s*immutable\s*$/m.test(cacheHeaders)) {
    throw new Error('Static cache policy must mark Vite fingerprinted assets immutable for one year')
  }

  const sourceFiles = (await readdir(canonicalArticles, { withFileTypes: true }))
    .filter((entry) => entry.isFile() && entry.name.endsWith('.md'))
    .map((entry) => entry.name)
    .sort()
  if (sourceFiles.length === 0) throw new Error('Canonical docs/articles corpus is empty')

  const articleData = await Promise.all(sourceFiles.map(async (file) => ({
    file,
    slug: getSlug(file, await readFile(path.join(canonicalArticles, file), 'utf8')),
  })))
  const expectedSlugs = articleData.map((article) => article.slug)
  if (new Set(expectedSlugs).size !== expectedSlugs.length) throw new Error('Canonical article slugs are not unique')
  if (expectedSlugs.some((slug) => !/^[a-z0-9-]+$/.test(slug))) throw new Error('Canonical article slug is not URL-safe')

  const expectedCanonical = new Map([
    ['index.html', absolute('')],
    ['reference/index.html', absolute('reference/')],
    ['docs/index.html', absolute('reference/')],
    ['articles/index.html', absolute('articles/')],
    ...expectedSlugs.map((slug) => [
      'articles/' + slug + '/index.html',
      absolute('articles/' + encodeURIComponent(slug) + '/'),
    ]),
  ])

  const files = await walkFiles(root)
  const htmlPages = files.filter((file) => file.endsWith('.html'))
  if (htmlPages.length !== expectedCanonical.size) {
    throw new Error('Unexpected prerendered HTML page count: expected ' + expectedCanonical.size + ', found ' + htmlPages.length)
  }
  for (const file of htmlPages) {
    const html = await readFile(path.join(root, file), 'utf8')
    const expected = expectedCanonical.get(file)
    if (!expected) throw new Error('Unexpected HTML route in static output: ' + file)
    if (canonicalHref(html) !== expected) {
      throw new Error('Non-canonical or missing canonical URL in ' + file + '; expected ' + expected)
    }
    if (!html.includes('favicon.svg')) throw new Error('Project favicon link missing from prerendered page: ' + file)
  }

  const legacyDocs = await readFile(path.join(root, 'docs', 'index.html'), 'utf8')
  if (!legacyDocs.includes('http-equiv="refresh"') || !legacyDocs.includes('url=' + base + 'reference/')) {
    throw new Error('Legacy /docs/ page must provide a static redirect fallback to /reference/')
  }

  const redirectLines = (await readFile(path.join(root, '_redirects'), 'utf8')).trim().split(/\r?\n/)
  const expectedRedirects = [
    base + 'reference ' + base + 'reference/ 301',
    base + 'docs ' + base + 'reference/ 301',
    base + 'docs/ ' + base + 'reference/ 301',
    base + 'articles ' + base + 'articles/ 301',
    ...expectedSlugs.map((slug) => {
      const source = base + 'articles/' + encodeURIComponent(slug)
      return source + ' ' + source + '/ 301'
    }),
  ]
  if (JSON.stringify(redirectLines) !== JSON.stringify(expectedRedirects)) {
    throw new Error('Static redirects do not match the canonical route policy')
  }

  const expectedUrls = [
    absolute(''),
    absolute('reference/'),
    absolute('articles/'),
    ...expectedSlugs.map((slug) => absolute('articles/' + encodeURIComponent(slug) + '/')),
  ]
  const sitemap = await readFile(path.join(root, 'sitemap.xml'), 'utf8')
  const sitemapUrls = [...sitemap.matchAll(/<loc>(.*?)<\/loc>/g)].map((match) => match[1])
  if (JSON.stringify(sitemapUrls) !== JSON.stringify(expectedUrls)) {
    throw new Error('Sitemap URLs do not match the canonical static routes')
  }
  if (sitemap.includes('/docs/')) throw new Error('Legacy /docs/ alias must not appear in the sitemap')

  const robots = await readFile(path.join(root, 'robots.txt'), 'utf8')
  if (!robots.includes('Allow: ' + base) || !robots.includes('Sitemap: ' + absolute('sitemap.xml'))) {
    throw new Error('robots.txt does not advertise the configured base path and sitemap')
  }

  const feed = await readFile(path.join(root, 'rss.xml'), 'utf8')
  const feedItems = [...feed.matchAll(/<item>/g)].length
  if (feedItems !== expectedSlugs.length) {
    throw new Error('RSS item count mismatch: expected ' + expectedSlugs.length + ', found ' + feedItems)
  }
  const feedLinks = [...feed.matchAll(/<item>[\s\S]*?<link>(.*?)<\/link>[\s\S]*?<\/item>/g)].map((match) => match[1])
  const expectedFeedLinks = expectedSlugs.slice().reverse().map((slug) =>
    absolute('articles/' + encodeURIComponent(slug) + '/'),
  )
  if (JSON.stringify(feedLinks) !== JSON.stringify(expectedFeedLinks)) {
    throw new Error('RSS links do not match canonical article URLs')
  }

  const favicon = await readFile(path.join(root, 'favicon.svg'), 'utf8')
  if (!favicon.includes('<svg') || !favicon.includes('</svg>')) throw new Error('Project favicon is not a valid SVG document')

  const forbidden = files.filter((file) =>
    /(^|\/)(?:server|functions|\.netlify|_serverFn)(?:\/|$)/i.test(file),
  )
  if (forbidden.length) throw new Error('Server/runtime artifacts found in static output: ' + forbidden.join(', '))

  const runtimeFiles = files.filter((file) => /\.(?:html|js|mjs|json)$/i.test(file))
  for (const file of runtimeFiles) {
    const content = await readFile(path.join(root, file), 'utf8')
    if (content.includes('/_serverFn') || content.includes('/.netlify/functions')) {
      throw new Error('Server-function endpoint reference found in deployable file: ' + file)
    }
  }

  const broken = await findBrokenLocalReferences(root, base)
  if (broken.length) throw new Error('Broken local references (' + broken.length + '):\n- ' + broken.join('\n- '))

  const summary = {
    htmlPages: htmlPages.length,
    articlePages: expectedSlugs.length,
    canonicalUrls: expectedUrls.length,
    rssItems: feedItems,
    basePath: base,
  }
  console.log('[static-dist] verified ' + summary.htmlPages + ' HTML pages, ' +
    summary.articlePages + ' articles, canonical URLs, RSS, sitemap, redirects, cache headers, and local references at ' + summary.basePath)
  return summary
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const distRoot = process.argv[2] || path.join(websiteRoot, 'dist', 'client')
  const basePath = process.argv[3] || process.env.PUBLIC_BASE_PATH || '/'
  validateDist(distRoot, basePath, process.env.SITE_URL).catch((error) => {
    console.error(error.message)
    process.exitCode = 1
  })
}
