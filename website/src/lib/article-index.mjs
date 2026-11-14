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
  const key = href
    .split(/[?#]/, 1)[0]
    .replace(/^\.?\//, "")
    .replace(/\/$/, "")
    .replace(/\.md$/, "")
    .toLowerCase();
  if (!key || key.includes("/") || key.includes(".") || key.includes(":")) return null;

  const stripNumericPrefix = (value) => value.toLowerCase().replace(/^\d+-/, "");
  const uniqueMatch = (matches) => {
    const ids = [...new Set(matches.map((article) => article.id))];
    return ids.length === 1 ? ids[0] : null;
  };

  // A file identity is authoritative and takes precedence over editorial slugs.
  const exactId = articles.filter((article) => article.id.toLowerCase() === key);
  if (exactId.length) return uniqueMatch(exactId);

  const exactSlug = articles.filter(
    (article) => article.slug?.toLowerCase() === key
  );
  if (exactSlug.length) return uniqueMatch(exactSlug);

  const normalizedId = articles.filter(
    (article) => stripNumericPrefix(article.id) === stripNumericPrefix(key)
  );
  if (normalizedId.length) return uniqueMatch(normalizedId);

  const normalizedSlug = articles.filter(
    (article) =>
      article.slug &&
      stripNumericPrefix(article.slug) === stripNumericPrefix(key)
  );
  if (normalizedSlug.length) return uniqueMatch(normalizedSlug);

  const want = tokens(key);
  let bestScore = 0;
  const bestIds = new Set();
  for (const article of articles) {
    let articleScore = 0;
    for (const candidate of [article.slug, article.id]) {
      if (!candidate) continue;
      const have = tokens(candidate);
      const inter = [...want].filter((token) => have.has(token)).length;
      const score = inter / new Set([...want, ...have]).size;
      articleScore = Math.max(articleScore, score);
    }
    if (articleScore > bestScore) {
      bestScore = articleScore;
      bestIds.clear();
      bestIds.add(article.id);
    } else if (articleScore === bestScore && articleScore > 0) {
      bestIds.add(article.id);
    }
  }

  return bestScore >= 0.5 && bestIds.size === 1
    ? bestIds.values().next().value
    : null;
}