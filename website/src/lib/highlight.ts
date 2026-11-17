/**
 * Tiny, dependency-free highlighter shared by <CodeBlock> and the article
 * renderer. It returns plain tokens so callers can render React nodes or HTML.
 */
export type Token = { text: string; cls?: string }

const PY_KEYWORDS = new Set([
  'from',
  'import',
  'class',
  'def',
  'return',
  'True',
  'False',
  'None',
  'as',
  'if',
  'else',
  'elif',
  'for',
  'in',
  'with',
  'pass',
  'raise',
  'try',
  'except',
  'not',
  'and',
  'or',
  'is',
  'lambda',
  'yield',
])

const PY_RE =
  /(#[^\n]*)|("""[\s\S]*?"""|'''[\s\S]*?'''|"(?:[^"\\\n]|\\.)*"|'(?:[^'\\\n]|\\.)*')|(@[A-Za-z_][\w.]*)|\b(\d+)\b|\b([A-Za-z_]\w*)(?=\()|\b([A-Za-z_]\w*)\b/g

function tokenizePython(code: string): Token[] {
  const out: Token[] = []
  const re = new RegExp(PY_RE.source, 'g')
  let last = 0
  let m: RegExpExecArray | null
  while ((m = re.exec(code))) {
    if (m.index > last) out.push({ text: code.slice(last, m.index) })
    const [t] = m
    if (m[1]) out.push({ text: t, cls: 'tok-com' })
    else if (m[2]) out.push({ text: t, cls: 'tok-str' })
    else if (m[3]) out.push({ text: t, cls: 'tok-dec' })
    else if (m[4]) out.push({ text: t, cls: 'tok-num' })
    else if (m[5]) out.push({ text: t, cls: PY_KEYWORDS.has(t) ? 'tok-kw' : 'tok-fn' })
    else if (m[6] && PY_KEYWORDS.has(t)) out.push({ text: t, cls: 'tok-kw' })
    else out.push({ text: t })
    last = m.index + t.length
  }
  if (last < code.length) out.push({ text: code.slice(last) })
  return out
}

function tokenizeShell(code: string): Token[] {
  const out: Token[] = []
  code.split('\n').forEach((line, i, lines) => {
    if (line.startsWith('#')) out.push({ text: line, cls: 'tok-com' })
    else if (line.startsWith('$ ')) {
      out.push({ text: '$ ', cls: 'tok-prompt' })
      out.push({ text: line.slice(2) })
    } else out.push({ text: line })
    if (i < lines.length - 1) out.push({ text: '\n' })
  })
  return out
}

export function tokenize(code: string, lang = 'python'): Token[] {
  if (lang === 'python' || lang === 'py') return tokenizePython(code)
  if (lang === 'bash' || lang === 'sh' || lang === 'shell' || lang === 'text') return tokenizeShell(code)
  return [{ text: code }]
}

export function escapeHtml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

export function highlightToHtml(code: string, lang = 'python'): string {
  return tokenize(code, lang)
    .map((t) => (t.cls ? `<span class="${t.cls}">${escapeHtml(t.text)}</span>` : escapeHtml(t.text)))
    .join('')
}
