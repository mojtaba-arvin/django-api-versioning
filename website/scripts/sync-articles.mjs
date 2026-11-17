// Copies the canonical article corpus from the repository into the website build input.
// Usage: pnpm run sync:articles
import { copyFile, mkdir, readdir, rm } from 'node:fs/promises'
import { join } from 'node:path'

const repositoryRoot = join(import.meta.dirname, '..', '..')
const source = join(repositoryRoot, 'docs', 'articles')
const output = join(import.meta.dirname, '..', 'content', 'articles')

const entries = (await readdir(source, { withFileTypes: true }))
  .filter((entry) => entry.isFile() && /^[\\w.-]+\\.md$/.test(entry.name))
  .map((entry) => entry.name)
  .sort()

if (entries.length === 0) {
  throw new Error(`No Markdown articles found in canonical source: ${source}`)
}

await mkdir(output, { recursive: true })
const expected = new Set(entries)
for (const name of await readdir(output)) {
  if (name.endsWith('.md') && !expected.has(name)) {
    await rm(join(output, name))
  }
}

for (const name of entries) {
  await copyFile(join(source, name), join(output, name))
}

console.log(`Copied ${entries.length} canonical articles from docs/articles/.`)
