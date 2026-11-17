import { createFileRoute, notFound } from '@tanstack/react-router'
import { ArticlePage } from '../components/ArticlePage'
import { site, rssHref } from '../data/site'
import { getArticle } from '../lib/article-data'

export const Route = createFileRoute('/articles/$slug')({
  loader: async ({ params }) => {
    const article = getArticle(params.slug)
    if (!article) throw notFound()
    return article
  },
  component: function ArticleRoute() {
    return <ArticlePage article={Route.useLoaderData()} />
  },
  head: ({ loaderData }) => ({
    meta: loaderData
      ? [
          { title: `${loaderData.title} · ${site.name}` },
          { name: 'description', content: loaderData.description },
          { name: 'keywords', content: loaderData.keywords.join(', ') },
          { name: 'author', content: loaderData.author.name },
          { property: 'og:title', content: loaderData.title },
          { property: 'og:description', content: loaderData.description },
          { property: 'og:type', content: 'article' },
        ]
      : [],
    links: [{ rel: 'alternate', type: 'application/rss+xml', title: `${site.name} articles`, href: rssHref }],
  }),
})
