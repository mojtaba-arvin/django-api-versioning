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
    const { html, toc } = renderReferenceMarkdown(markdown)
    expect(toc.map((item) => item.text)).toEqual([
      'Installation',
      'Settings',
      '@endpoint arguments',
      'Validation & collisions',
      'Exceptions',
      'Management commands',
      'Development',
    ])
    expect(html).toContain('reference-code')
    expect(html).toContain('reference-table')
    expect(html).toContain('data-copy')
    expect(html).toContain('MyViewSet.as_view({&quot;get&quot;: &quot;list&quot;})')
  })
})
