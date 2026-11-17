import { readFileSync, readdirSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { parseArticle, parseFrontmatter, renderMarkdown, slugify } from './articles'

const sample = `---
slug: "007-example"
title: "An \\"example\\" title"
description: "Short summary."
author:
  name: "Mojtaba Arvin"
  url: "https://example.com/"
keywords:
  - "Django API versioning"
  - "DRF"
---

# An example title

Intro with \`code\` and a [link](https://example.com).

## First section

\`\`\`python
from django_api_versioning import endpoint
\`\`\`

## First section

| a | b |
|---|---|
| 1 | <2> |
`

describe('parseFrontmatter', () => {
  it('reads scalars, nested maps and lists', () => {
    const { data, body } = parseFrontmatter(sample)
    expect(data.slug).toBe('007-example')
    expect(data.title).toBe('An "example" title')
    expect(data.author).toEqual({ name: 'Mojtaba Arvin', url: 'https://example.com/' })
    expect(data.keywords).toEqual(['Django API versioning', 'DRF'])
    expect(body.startsWith('\n# An example title')).toBe(true)
  })

  it('returns the raw text when there is no front matter', () => {
    expect(parseFrontmatter('# Hi').body).toBe('# Hi')
  })
})

describe('renderMarkdown', () => {
  const { html, toc } = renderMarkdown(parseFrontmatter(sample).body)

  it('drops the leading h1 and builds a unique h2 table of contents', () => {
    expect(html).not.toContain('<h1')
    expect(toc).toEqual([
      { id: 'first-section', text: 'First section' },
      { id: 'first-section-1', text: 'First section' },
    ])
  })

  it('highlights code and escapes table content', () => {
    expect(html).toContain('<span class="tok-kw">from</span>')
    expect(html).toContain('data-copy')
    expect(html).toContain('&lt;2&gt;')
    expect(html).toContain('class="table-wrap"')
    expect(html).toContain('rel="noopener noreferrer"')
  })
})

describe('parseArticle', () => {
  it('derives metadata from the file name and front matter', () => {
    const a = parseArticle('/content/articles/007-example.md', sample)
    expect(a.number).toBe(7)
    expect(a.slug).toBe('007-example')
    expect(a.title).toBe('An "example" title')
    expect(a.sourceUrl).toMatch(/docs\/articles\/007-example\.md$/)
    expect(a.readingMinutes).toBeGreaterThanOrEqual(1)
  })

  it('parses every vendored article with a title, description and sections', () => {
    const dir = join(__dirname, '../../content/articles')
    const files = readdirSync(dir).filter((f) => f.endsWith('.md'))
    expect(files.length).toBeGreaterThan(0)
    const slugs = new Set<string>()
    for (const f of files) {
      const a = parseArticle(f, readFileSync(join(dir, f), 'utf8'))
      expect(a.title, f).not.toBe('')
      expect(a.description, f).not.toBe('')
      expect(a.toc.length, f).toBeGreaterThan(0)
      expect(a.slug, f).toMatch(/^[a-z0-9-]+$/)
      slugs.add(a.slug)
    }
    expect(slugs.size).toBe(files.length)
  })

  it('keeps the generated website corpus byte-for-byte aligned with the repository source', () => {
    const generatedDir = join(__dirname, '../../content/articles')
    const canonicalDir = join(__dirname, '../../../docs/articles')
    const generated = readdirSync(generatedDir).filter((f) => f.endsWith('.md')).sort()
    const canonical = readdirSync(canonicalDir).filter((f) => f.endsWith('.md')).sort()

    expect(generated).toEqual(canonical)
    for (const file of canonical) {
      expect(readFileSync(join(generatedDir, file), 'utf8'), file).toBe(
        readFileSync(join(canonicalDir, file), 'utf8'),
      )
    }
  })
})

describe('slugify', () => {
  it('normalises headings', () => {
    expect(slugify('Option 1: explicit Django URL patterns')).toBe('option-1-explicit-django-url-patterns')
  })
})
