import { createFileRoute } from '@tanstack/react-router'
import { HomePage } from '../components/HomePage'
import { getArticleList } from '../server/articles'

export const Route = createFileRoute('/')({
  loader: () => getArticleList(),
  component: function HomeRoute() {
    return <HomePage articles={Route.useLoaderData()} />
  },
})
