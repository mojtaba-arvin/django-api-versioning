// Copy the canonical Reference Markdown into the website's local build input.
// Usage: pnpm run sync:reference
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import { dirname, join } from 'node:path'

const websiteRoot = join(import.meta.dirname, '..')
const repositoryRoot = join(websiteRoot, '..')
const source = join(repositoryRoot, 'docs', 'reference', 'index.md')
const output = join(websiteRoot, 'content', 'reference', 'index.md')

const markdown = await readFile(source, 'utf8')
if (!/^# .+\r?\n/m.test(markdown) || !/^## Installation\s*$/m.test(markdown)) {
  throw new Error('Canonical Reference Markdown is missing its title or Installation section: ' + source)
}

await mkdir(dirname(output), { recursive: true })
await writeFile(output, markdown, 'utf8')
console.log('Synced canonical Reference content from docs/reference/index.md.')
