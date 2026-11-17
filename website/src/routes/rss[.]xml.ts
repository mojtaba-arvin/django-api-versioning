import { createFileRoute } from '@tanstack/react-router'
import { site } from '../data/site'
import { escapeHtml } from '../lib/highlight'
import { loadArticles } from '../server/articles'

export const Route = createFileRoute('/rss.xml')({
  server: {
    handlers: {
      GET: ({ request }) => {
        const origin = new URL(request.url).origin
        const items = loadArticles()
          .slice()
          .reverse()
          .map((a) => {
            const link = `${origin}/articles/${a.slug}`
            return [
              '<item>',
              `<title>${escapeHtml(a.title)}</title>`,
              `<link>${link}</link>`,
              `<guid isPermaLink="true">${link}</guid>`,
              `<description>${escapeHtml(a.description)}</description>`,
              `<dc:creator>${escapeHtml(a.author.name)}</dc:creator>`,
              ...a.keywords.map((k) => `<category>${escapeHtml(k)}</category>`),
              '</item>',
            ].join('')
          })
          .join('\n')
        const xml = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom" xmlns:dc="http://purl.org/dc/elements/1.1/">
<channel>
<title>${escapeHtml(site.name)} articles</title>
<link>${origin}/articles</link>
<atom:link href="${origin}/rss.xml" rel="self" type="application/rss+xml" />
<description>Guides on Django and DRF API versioning from the django-api-versioning project.</description>
<language>en</language>
${items}
</channel>
</rss>`
        return new Response(xml, {
          headers: {
            'content-type': 'application/rss+xml; charset=utf-8',
            'cache-control': 'public, max-age=0, must-revalidate',
            'netlify-cdn-cache-control': 'public, max-age=3600, stale-while-revalidate=86400',
          },
        })
      },
    },
  },
})
