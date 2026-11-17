import { createFileRoute } from '@tanstack/react-router'
import { ArticlesPage } from '../components/ArticlesPage'
import { canonicalUrl, site, rssHref } from '../data/site'
import { getArticleList } from '../lib/article-data'

export const Route = createFileRoute('/articles/')({
  loader: () => getArticleList(),
  component: function ArticlesRoute() {
    return <ArticlesPage articles={Route.useLoaderData()} />
  },
  head: () => ({
    meta: [
      { title: `Articles · ${site.name}` },
      {
        name: 'description',
        content:
          'Long-form guides on Django and DRF API versioning: routing models, inheriting endpoints between versions, deprecation headers, reverse lookups and migrations.',
      },
    ],
    links: [
      { rel: 'alternate', type: 'application/rss+xml', title: `${site.name} articles`, href: rssHref },
      ...(canonicalUrl('articles/') ? [{ rel: 'canonical', href: canonicalUrl('articles/')! }] : []),
    ],
  }),
})
