import { Marked, type Tokens } from 'marked'
import { escapeHtml, highlightToHtml } from './highlight'

export type ReferenceTocEntry = { id: string; text: string }

function inlineText(tokens: Tokens.Generic[]): string {
  return tokens.map((token) => {
    if (token.type === 'html') return ''
    if ('tokens' in token && Array.isArray(token.tokens)) {
      return inlineText(token.tokens as Tokens.Generic[])
    }
    return 'text' in token && typeof token.text === 'string' ? token.text : ''
  }).join('')
}

function slugify(text: string): string {
  return text.toLowerCase().replace(/&[a-z#0-9]+;/g, '')
    .replace(/[^a-z0-9\s-]/g, '').trim().replace(/\s+/g, '-').replace(/-+/g, '-')
}

/** Render canonical Reference Markdown for the /reference/ page. */
export function renderReferenceMarkdown(body: string): { title: string; html: string; toc: ReferenceTocEntry[] } {
  const title = body.split(/\r?\n/).find((line) => /^#\s/.test(line))?.replace(/^#\s+/, '').trim() ?? ''
  const toc: ReferenceTocEntry[] = []
  const used = new Map<string, number>()
  let skippedTitle = false
  const marked = new Marked({ gfm: true })

  marked.use({
    renderer: {
      html({ text }: Tokens.HTML) {
        // Raw HTML in canonical Markdown must remain inert in generated pages.
        return escapeHtml(text)
      },
      heading({ tokens, depth }: Tokens.Heading) {
        const inner = this.parser.parseInline(tokens)
        if (depth === 1 && !skippedTitle) {
          skippedTitle = true
          return ''
        }
        const level = Math.max(2, depth)
        const plain = inlineText(tokens)
        let id = slugify(plain) || 'section'
        const count = used.get(id) ?? 0
        used.set(id, count + 1)
        if (count) id = id + '-' + count
        if (level === 2) toc.push({ id, text: plain })
        return '<h' + level + ' id="' + id + '" class="reference-heading"><a class="reference-heading-link" href="#' + id + '">' + inner + '</a> <span class="reference-heading-mark">#</span></h' + level + '>\n'
      },
      code({ text, lang }: Tokens.Code) {
        const info = (lang ?? '').trim()
        const language = info.split(/\s+/)[0] || 'text'
        const titleMatch = /\btitle=(?:"([^"]+)"|'([^']+)'|([^\s]+))/.exec(info)
        const title = titleMatch?.[1] ?? titleMatch?.[2] ?? titleMatch?.[3] ?? language
        return '<div class="card overflow-hidden reference-code"><div class="flex items-center justify-between border-b border-line bg-ink-3/60 px-4 py-2">' +
          '<div class="flex items-center gap-2"><span class="flex gap-1.5" aria-hidden="true"><span class="h-2.5 w-2.5 rounded-full bg-line"></span><span class="h-2.5 w-2.5 rounded-full bg-line"></span><span class="h-2.5 w-2.5 rounded-full bg-line"></span></span>' +
          '<span class="ml-2 font-mono text-xs text-mute">' + escapeHtml(title) + '</span></div>' +
          '<button type="button" class="reference-copy" data-copy aria-label="Copy code to clipboard">Copy</button></div>' +
          '<pre><code>' + highlightToHtml(text, language) + '</code></pre></div>\n'
      },
      link({ href, title, tokens }: Tokens.Link) {
        const inner = this.parser.parseInline(tokens)
        const external = /^https?:\/\//.test(href)
        const titleAttribute = title ? ' title="' + escapeHtml(title) + '"' : ''
        const externalAttributes = external ? ' rel="noopener noreferrer"' : ''
        return '<a href="' + escapeHtml(href) + '"' + titleAttribute + externalAttributes + '>' + inner + '</a>'
      },
      table(token: Tokens.Table) {
        const head = token.header.map((cell) => '<th' + (cell.align ? ' style="text-align:' + cell.align + '"' : '') + '>' + this.parser.parseInline(cell.tokens) + '</th>').join('')
        const rows = token.rows.map((row) => '<tr>' + row.map((cell) => '<td' + (cell.align ? ' style="text-align:' + cell.align + '"' : '') + '>' + this.parser.parseInline(cell.tokens) + '</td>').join('') + '</tr>').join('')
        return '<div class="table-wrap reference-table"><table data-columns="' + token.header.length + '"><thead><tr>' + head + '</tr></thead><tbody>' + rows + '</tbody></table></div>\n'
      },
    },
  })

  return { title, html: marked.parse(body, { async: false }) as string, toc }
}
