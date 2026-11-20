import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { renderReferenceMarkdown } from './reference-markdown'

const canonicalPath = join(__dirname, '../../../docs/reference/index.md')
const generatedPath = join(__dirname, '../../content/reference/index.md')
const markdown = readFileSync(canonicalPath, 'utf8')

describe('canonical Reference content', () => {
  it('keeps the generated website input byte-for-byte aligned with docs/reference/index.md', () => {
    expect(readFileSync(generatedPath, 'utf8')).toBe(markdown)
  })

  it('renders every Reference section and preserves the existing presentation hooks', () => {
    const { title, html, toc } = renderReferenceMarkdown(markdown)
    expect(title).toBe('django-api-versioning reference')
    expect(toc.map((item) => item.text)).toEqual([
      'Installation',
      'Settings',
      '@endpoint arguments',
      'URL reversal',
      'Validation and collisions',
      'Explicit endpoint removal (available since 1.2.0)',
      'Exceptions',
      'Route-matrix tools',
      'API lifecycle',
      'Management commands',
      'Development',
    ])
    expect(html).toContain('reference-code')
    expect(html).toContain('reference-table')
    expect(html).toContain('data-copy')
    expect(html).toContain('ItemViewSet.as_view({&quot;get&quot;: &quot;list&quot;})')
  })

  it('keeps raw HTML inert in Reference Markdown', () => {
    const result = renderReferenceMarkdown('# Title\n\n## Safe <img src=x onerror=alert(1)> heading\n\n<script>alert(1)</script>')
    expect(result.html).not.toContain('<script>')
    expect(result.html).not.toContain('<img')
    expect(result.html).toContain('&lt;script&gt;')
    expect(result.toc).toEqual([{ id: 'safe-heading', text: 'Safe  heading' }])
  })
})
