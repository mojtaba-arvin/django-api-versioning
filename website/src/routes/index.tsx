import { createFileRoute } from '@tanstack/react-router'
import { HomePage } from '../components/HomePage'
import { canonicalUrl } from '../data/site'
import { getArticleList } from '../lib/article-data'

export const Route = createFileRoute('/')({
  loader: () => getArticleList(),
  component: function HomeRoute() {
    return <HomePage articles={Route.useLoaderData()} />
  },
  head: () => ({
    links: canonicalUrl() ? [{ rel: 'canonical', href: canonicalUrl()! }] : [],
  }),
})
