import { defineConfig } from 'vite'
import { tanstackStart } from '@tanstack/react-start/plugin/vite'
import viteReact from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

function normalizeSiteOrigin(value: string, allowLocalHttp: boolean): string {
  const parsed = new URL(value)
  const isLocalHttp = allowLocalHttp && parsed.protocol === 'http:' && parsed.hostname === 'localhost'
  if (
    (parsed.protocol !== 'https:' && !isLocalHttp) ||
    parsed.pathname !== '/' ||
    parsed.search ||
    parsed.hash ||
    parsed.username ||
    parsed.password
  ) {
    throw new Error('SITE_URL must be an HTTPS origin without a path, query, or credentials.')
  }
  return parsed.origin
}

export default defineConfig(({ command, mode }) => {
  const rawSiteUrl = process.env.SITE_URL || ''
  const siteOrigin = rawSiteUrl ? normalizeSiteOrigin(rawSiteUrl, command !== 'build') : ''

  if (command === 'build' && mode === 'production' && !siteOrigin) {
    throw new Error('Set SITE_URL to the public site origin before creating a production build.')
  }

  const rawBasePath = process.env.PUBLIC_BASE_PATH ?? '/'
  if (
    (rawBasePath && !rawBasePath.startsWith('/')) ||
    rawBasePath.startsWith('//') ||
    /[?#\\]/.test(rawBasePath)
  ) {
    throw new Error('PUBLIC_BASE_PATH must be a root-relative path without query, hash, or backslashes.')
  }
  const baseSegments = rawBasePath.split('/').filter(Boolean)
  if (baseSegments.some((segment) =>
    segment === '.' || segment === '..' || !/^[A-Za-z0-9._~-]+$/.test(segment)
  )) {
    throw new Error('PUBLIC_BASE_PATH contains an invalid URL path segment.')
  }
  const basePath = baseSegments.length ? '/' + baseSegments.join('/') + '/' : '/'
  const routerBasepath = basePath === '/' ? '/' : basePath.slice(0, -1)

  return {
    base: basePath,
    define: {
      __SITE_ORIGIN__: JSON.stringify(siteOrigin),
    },
    resolve: { tsconfigPaths: true },
    plugins: [
      tailwindcss(),
      tanstackStart({
        router: { basepath: routerBasepath },
        prerender: {
          enabled: true,
          autoSubfolderIndex: true,
          crawlLinks: true,
          failOnError: true,
          retryCount: 2,
        },
      }),
      viteReact(),
    ],
  }
})
