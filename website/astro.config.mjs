// @ts-check
import { defineConfig } from "astro/config";
import { remarkArticleLinks } from "./src/lib/remark-article-links.mjs";
import { rehypeHeadingAnchors } from "./src/lib/rehype-heading-anchors.mjs";

// Fully static output: `dist/` is plain files and works on any static server.
const rawBase = process.env.PUBLIC_BASE_PATH ?? "/";
const base = rawBase === "/" ? "/" : `/${rawBase.split("/").filter(Boolean).join("/")}`;

export default defineConfig({
  base,
  output: "static",
  // Netlify sets URL at build time; elsewhere, set SITE_URL to get canonical URLs.
  site: process.env.SITE_URL || process.env.URL || undefined,
  trailingSlash: "always",
  build: { format: "directory", inlineStylesheets: "auto" },
  prefetch: false,
  devToolbar: { enabled: false },
  markdown: {
    remarkPlugins: [remarkArticleLinks],
    rehypePlugins: [rehypeHeadingAnchors],
    shikiConfig: {
      themes: { light: "github-light", dark: "github-dark" },
      defaultColor: false,
      wrap: false,
    },
  },
});