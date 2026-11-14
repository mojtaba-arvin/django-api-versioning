// Shared by the remark plugin (build time, no Astro APIs available) and pages.
import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";

const DIR = path.resolve("src/content/articles");

const tokens = (s) =>
  new Set(
    s
      .toLowerCase()
      .replace(/^\d+-/, "")
      .split(/[^a-z0-9]+/)
      .filter(Boolean)
  );

/** [{ id, slug, stem }] for every mirrored article. */
export function listArticles() {
  return readdirSync(DIR)
    .filter((f) => f.endsWith(".md"))
    .sort()
    .map((file) => {
      const id = file.replace(/\.md$/, "");
      const text = readFileSync(path.join(DIR, file), "utf8");
      const slug = /^slug:\s*"?([^"\n]+)"?\s*$/m.exec(text)?.[1] ?? null;
      return { id, slug };
    });
}

/**
 * Resolve an upstream site-relative link such as
 * "/deprecate-old-django-api-versions-sunset-headers/" to an article id.
 * Exact match on slug or file name (with or without the numeric prefix)
 * first; otherwise the best token overlap (Jaccard >= 0.5).
 */
export function resolveArticleLink(href, articles = listArticles()) {
  const key = href.replace(/^\.?\//, "").replace(/\/$/, "").replace(/\.md$/, "").toLowerCase();
  if (!key || key.includes("/") || key.includes(".") || key.includes(":")) return null;
  const strip = (s) => (s ?? "").toLowerCase().replace(/^\d+-/, "");
  const exact = articles.find(
    (a) => [a.id, a.slug].some((v) => v && (v.toLowerCase() === key || strip(v) === strip(key)))
  );
  if (exact) return exact.id;
  const want = tokens(key);
  let best = null;
  let bestScore = 0;
  for (const a of articles) {
    for (const candidate of [a.slug, a.id]) {
      if (!candidate) continue;
      const have = tokens(candidate);
      const inter = [...want].filter((t) => have.has(t)).length;
      const score = inter / new Set([...want, ...have]).size;
      if (score > bestScore) [best, bestScore] = [a.id, score];
    }
  }
  return bestScore >= 0.5 ? best : null;
}