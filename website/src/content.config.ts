import { defineCollection } from "astro:content";
import { glob } from "astro/loaders";
import { z } from "astro/zod";

/**
 * Every Markdown file mirrored from upstream `docs/articles/` is published.
 * IDs come from the FILE NAME, not the frontmatter `slug`: upstream 003 and
 * 004 share the slug "004-api-routing-library", so slugs are not unique.
 */
const articles = defineCollection({
  loader: glob({
    pattern: "*.md",
    base: "./src/content/articles",
    generateId: ({ entry }) => entry.replace(/\.md$/, ""),
  }),
  schema: z.object({
    title: z.string().optional(),
    description: z.string().optional(),
    slug: z.string().optional(),
    keywords: z.array(z.string()).optional(),
    author: z.object({ name: z.string(), url: z.string().optional() }).optional(),
  }),
});

export const collections = { articles };