import { parseArticle, toMeta, type Article, type ArticleMeta } from './articles'

// The article corpus is bundled from the repository-local generated build input.
// This module is shared by route loaders and contains no server endpoints.
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

export function getArticleList(): ArticleMeta[] {
  return loadArticles().map(toMeta)
}

export type ArticleWithNeighbours = Article & {
  prev: ArticleMeta | null
  next: ArticleMeta | null
}

export function getArticle(slug: string): ArticleWithNeighbours | null {
  const all = loadArticles()
  const index = all.findIndex((article) => article.slug === slug)
  if (index === -1) return null
  return {
    ...all[index],
    prev: index > 0 ? toMeta(all[index - 1]) : null,
    next: index < all.length - 1 ? toMeta(all[index + 1]) : null,
  }
}
