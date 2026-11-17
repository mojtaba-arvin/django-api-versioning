import { defineConfig } from 'vite'
import { tanstackStart } from '@tanstack/react-start/plugin/vite'
import viteReact from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

const rawBasePath = process.env.PUBLIC_BASE_PATH ?? '/'
const basePath = rawBasePath === '/' ? '/' : `/${rawBasePath.split('/').filter(Boolean).join('/')}/`
const routerBasepath = basePath === '/' ? '/' : basePath.slice(0, -1)

export default defineConfig({
  base: basePath,
  resolve: { tsconfigPaths: true },
  plugins: [
    tailwindcss(),
    tanstackStart({
      router: { basepath: routerBasepath },
      prerender: {
        enabled: true,
        crawlLinks: true,
        failOnError: true,
        retryCount: 2,
      },
    }),
    viteReact(),
  ],
})
