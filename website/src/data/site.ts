export const site = {
  name: 'django-api-versioning',
  title: 'django-api-versioning — decorator-based API versioning for Django',
  description:
    'Declare a view once with @endpoint and get versioned URL patterns for Django and Django REST Framework. Later versions automatically reuse the most recent earlier implementation.',
  github: 'https://github.com/mojtaba-arvin/django-api-versioning',
  pypi: 'https://pypi.org/project/django-api-versioning/',
  author: 'Mojtaba Arvin',
  license: 'MIT',
  install: 'pip install django-api-versioning',
}

/** Build an absolute canonical URL for the configured origin and deployment base path. */
export function canonicalUrl(path = ''): string | undefined {
  if (!__SITE_ORIGIN__) return undefined
  const relativePath = path.replace(/^\/+/, '')
  return new URL(import.meta.env.BASE_URL + relativePath, __SITE_ORIGIN__ + '/').toString()
}

export const rssHref = `${import.meta.env.BASE_URL}rss.xml`

export const nav = [
  { label: 'Features', href: `${import.meta.env.BASE_URL}#features` },
  { label: 'Quick start', href: `${import.meta.env.BASE_URL}#quick-start` },
  { label: 'Playground', href: `${import.meta.env.BASE_URL}#playground` },
  { label: 'Lifecycle', href: `${import.meta.env.BASE_URL}#lifecycle` },
]
