import { defineCollection } from "astro:content";
import { glob } from "astro/loaders";
import { z } from "astro/zod";

/**
 * Every Markdown file mirrored from upstream `docs/articles/` is published.
 * IDs come from the FILE NAME, not the frontmatter `slug`. File identity keeps
 * article routes stable when editorial slugs change and avoids slug collisions.
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