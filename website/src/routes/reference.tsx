import { createFileRoute } from '@tanstack/react-router'
import { ReferencePage } from '../components/ReferencePage'
import { canonicalUrl, site } from '../data/site'

export const Route = createFileRoute('/reference')({
  component: ReferencePage,
  head: () => ({
    meta: [
      { title: `Reference · ${site.name}` },
      {
        name: 'description',
        content:
          'Settings, @endpoint arguments, collision rules, exceptions and management commands for django-api-versioning.',
      },
    ],
    links: canonicalUrl('reference/')
      ? [{ rel: 'canonical', href: canonicalUrl('reference/')! }]
      : [],
  }),
})
