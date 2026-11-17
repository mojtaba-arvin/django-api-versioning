import { createServerFn } from '@tanstack/react-start'
import { parseArticle, toMeta, type Article, type ArticleMeta } from '../lib/articles'

// Markdown is bundled into the server build only; the browser receives rendered HTML.
const files = import.meta.glob('../../content/articles/*.md', {
  query: '?raw',
  import: 'default',
  eager: true,
}) as Record<string, string>

let cache: Article[] | null = null

export function loadArticles(): Article[] {
  if (!cache) {
    cache = Object.entries(files)
      .map(([path, raw]) => parseArticle(path, raw))
      .sort((a, b) => a.number - b.number)
  }
  return cache
}

export const getArticleList = createServerFn({ method: 'GET' }).handler(
  async (): Promise<ArticleMeta[]> => loadArticles().map(toMeta),
)

export type ArticleWithNeighbours = Article & {
  prev: ArticleMeta | null
  next: ArticleMeta | null
}

export const getArticle = createServerFn({ method: 'GET' })
  .validator((slug: unknown) => {
    if (typeof slug !== 'string') throw new Error('Invalid slug')
    return slug
  })
  .handler(async ({ data: slug }): Promise<ArticleWithNeighbours | null> => {
    const all = loadArticles()
    const i = all.findIndex((a) => a.slug === slug)
    if (i === -1) return null
    return {
      ...all[i],
      prev: i > 0 ? toMeta(all[i - 1]) : null,
      next: i < all.length - 1 ? toMeta(all[i + 1]) : null,
    }
  })
