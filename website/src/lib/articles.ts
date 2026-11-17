import { Marked, type Tokens } from 'marked'
import { escapeHtml, highlightToHtml } from './highlight'

export type ArticleMeta = {
  slug: string
  number: number
  title: string
  description: string
  author: { name: string; url?: string }
  keywords: string[]
  readingMinutes: number
  sourceUrl: string
}

export type TocEntry = { id: string; text: string }

export type Article = ArticleMeta & { html: string; toc: TocEntry[] }

export const ARTICLES_SOURCE =
  'https://github.com/mojtaba-arvin/django-api-versioning/blob/main/docs/articles'

type Frontmatter = Record<string, string | string[] | Record<string, string>>

function unquote(v: string): string {
  const t = v.trim()
  if ((t.startsWith('"') && t.endsWith('"')) || (t.startsWith("'") && t.endsWith("'"))) {
    return t.slice(1, -1).replace(/\\"/g, '"')
  }
  return t
}

/**
 * Minimal YAML front-matter reader covering the shapes used by the upstream
 * articles: scalar strings, one-level nested maps and string lists.
 */
export function parseFrontmatter(raw: string): { data: Frontmatter; body: string } {
  const m = /^---\r?\n([\s\S]*?)\r?\n---\r?\n?/.exec(raw)
  if (!m) return { data: {}, body: raw }
  const data: Frontmatter = {}
  let current: string | null = null
  for (const line of m[1].split(/\r?\n/)) {
    if (!line.trim()) continue
    const top = /^([A-Za-z_][\w-]*):\s*(.*)$/.exec(line)
    if (top) {
      current = top[1]
      if (top[2]) {
        data[current] = unquote(top[2])
        current = null
      }
      continue
    }
    if (!current) continue
    const item = /^\s+-\s+(.*)$/.exec(line)
    if (item) {
      const list = Array.isArray(data[current]) ? (data[current] as string[]) : []
      list.push(unquote(item[1]))
      data[current] = list
      continue
    }
    const nested = /^\s+([A-Za-z_][\w-]*):\s*(.*)$/.exec(line)
    if (nested) {
      const map =
        data[current] && typeof data[current] === 'object' && !Array.isArray(data[current])
          ? (data[current] as Record<string, string>)
          : {}
      map[nested[1]] = unquote(nested[2])
      data[current] = map
    }
  }
  return { data, body: raw.slice(m[0].length) }
}

function inlineText(tokens: Tokens.Generic[]): string {
  return tokens.map((token) => {
    if (token.type === 'html') return ''
    if ('tokens' in token && Array.isArray(token.tokens)) {
      return inlineText(token.tokens as Tokens.Generic[])
    }
    return 'text' in token && typeof token.text === 'string' ? token.text : ''
  }).join('')
}

export function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/&[a-z#0-9]+;/g, '')
    .replace(/[^a-z0-9\s-]/g, '')
    .trim()
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-')
}

/** Renders article markdown to HTML, collecting h2 entries for a table of contents. */
export function renderMarkdown(body: string): { html: string; toc: TocEntry[] } {
  const toc: TocEntry[] = []
  const used = new Map<string, number>()
  let skippedTitle = false

  const marked = new Marked({ gfm: true })
  marked.use({
    renderer: {
      html({ text }: Tokens.HTML) {
        // Raw HTML in repository Markdown must remain inert in generated pages.
        return escapeHtml(text)
      },
      heading({ tokens, depth }: Tokens.Heading) {
        const inner = this.parser.parseInline(tokens)
        // The page header already shows the title, so drop the leading h1.
        if (depth === 1 && !skippedTitle) {
          skippedTitle = true
          return ''
        }
        const level = Math.max(2, depth)
        const plain = inlineText(tokens)
        let id = slugify(plain) || 'section'
        const n = used.get(id) ?? 0
        used.set(id, n + 1)
        if (n) id = `${id}-${n}`
        if (level === 2) toc.push({ id, text: plain })
        return `<h${level} id="${id}"><a class="anchor" href="#${id}" aria-hidden="true" tabindex="-1">#</a>${inner}</h${level}>\n`
      },
      code({ text, lang }: Tokens.Code) {
        const language = (lang ?? '').trim().split(/\s+/)[0] || 'text'
        return (
          `<figure class="article-code"><figcaption><span>${escapeHtml(language)}</span>` +
          `<button type="button" class="copy-code" data-copy aria-label="Copy code to clipboard">Copy</button></figcaption>` +
          `<pre><code class="language-${escapeHtml(language)}">${highlightToHtml(text, language)}</code></pre></figure>\n`
        )
      },
      link({ href, title, tokens }: Tokens.Link) {
        const inner = this.parser.parseInline(tokens)
        const external = /^https?:\/\//.test(href)
        const t = title ? ` title="${escapeHtml(title)}"` : ''
        const ext = external ? ' rel="noopener noreferrer"' : ''
        return `<a href="${escapeHtml(href)}"${t}${ext}>${inner}</a>`
      },
      table(token: Tokens.Table) {
        const head = token.header
          .map((c) => `<th${c.align ? ` style="text-align:${c.align}"` : ''}>${this.parser.parseInline(c.tokens)}</th>`)
          .join('')
        const rows = token.rows
          .map(
            (r) =>
              `<tr>${r
                .map((c) => `<td${c.align ? ` style="text-align:${c.align}"` : ''}>${this.parser.parseInline(c.tokens)}</td>`)
                .join('')}</tr>`,
          )
          .join('')
        return `<div class="table-wrap"><table><thead><tr>${head}</tr></thead><tbody>${rows}</tbody></table></div>\n`
      },
    },
  })

  const html = marked.parse(body, { async: false }) as string
  return { html, toc }
}

function asString(v: unknown): string {
  return typeof v === 'string' ? v : ''
}

export function parseArticle(fileName: string, raw: string): Article {
  const { data, body } = parseFrontmatter(raw)
  const base = fileName.replace(/^.*\//, '').replace(/\.md$/, '')
  const slug = asString(data.slug) || base
  const number = Number.parseInt(/^(\d+)/.exec(base)?.[1] ?? '0', 10)
  const h1 = /^#\s+(.+)$/m.exec(body)?.[1]
  const authorRaw = data.author
  const author =
    authorRaw && typeof authorRaw === 'object' && !Array.isArray(authorRaw)
      ? { name: authorRaw.name ?? '', url: authorRaw.url }
      : { name: asString(authorRaw) }
  const words = body.replace(/```[\s\S]*?```/g, ' ').split(/\s+/).filter(Boolean).length
  const { html, toc } = renderMarkdown(body)
  return {
    slug,
    number,
    title: asString(data.title) || h1 || base,
    description: asString(data.description),
    author,
    keywords: Array.isArray(data.keywords) ? data.keywords : [],
    readingMinutes: Math.max(1, Math.round(words / 220)),
    sourceUrl: `${ARTICLES_SOURCE}/${base}.md`,
    html,
    toc,
  }
}

export function toMeta(a: Article): ArticleMeta {
  const { html: _html, toc: _toc, ...meta } = a
  return meta
}
