import { createFileRoute } from '@tanstack/react-router'
import { DocsPage } from '../components/DocsPage'
import { site } from '../data/site'

export const Route = createFileRoute('/docs')({
  component: DocsPage,
  head: () => ({
    meta: [
      { title: `Reference · ${site.name}` },
      {
        name: 'description',
        content:
          'Settings, @endpoint arguments, collision rules, exceptions and management commands for django-api-versioning.',
      },
    ],
  }),
})
