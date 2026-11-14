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
    title: z.string().min(1).max(70),
    description: z.string().min(1).max(160),
    slug: z
      .string()
      .max(100)
      .regex(/^\d{3}-[a-z0-9]+(?:-[a-z0-9]+)*$/),
    keywords: z.array(z.string().min(1).max(40)).min(2).max(5),
    author: z.object({
      name: z.literal("Mojtaba Arvin"),
      url: z.literal("https://www.linkedin.com/in/mojtabaarvin/"),
    }),
  }),
});

export const collections = { articles };