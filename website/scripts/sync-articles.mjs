#!/usr/bin/env node
/** Copy canonical Markdown articles and generate the static search index. */
import { createHash } from "node:crypto";
import { execFileSync } from "node:child_process";
import { copyFile, mkdir, readFile, readdir, rm, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { parseArticleMetadata } from "../src/lib/article-metadata.mjs";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const websiteRoot = path.resolve(scriptDirectory, "..");
const repositoryRoot = path.resolve(websiteRoot, "..");
const sourceDirectory = path.join(repositoryRoot, "docs", "articles");
const outputDirectory = path.join(websiteRoot, "src", "content", "articles");
const sourceFiles = (await readdir(sourceDirectory))
  .filter((name) => name.endsWith(".md"))
  .sort((a, b) => a.localeCompare(b, "en", { numeric: true }));
if (!sourceFiles.length) throw new Error("No canonical Markdown articles found in docs/articles.");

// Validate every source article before touching the generated mirror. A bad
// metadata change must not erase the last usable generated content.
const sourceEntries = await Promise.all(
  sourceFiles.map(async (name) => {
    const content = await readFile(path.join(sourceDirectory, name));
    const article = parseArticleMetadata(name, content);
    return { name, content, article };
  }),
);

const slugOwners = new Map();
for (const { name, article } of sourceEntries) {
  const previous = slugOwners.get(article.slug);
  if (previous) {
    throw new Error(
      "Duplicate article slug " + article.slug + " in " + previous + " and " + name + ".",
    );
  }
  slugOwners.set(article.slug, name);
}

// All source files and cross-article slugs are valid. It is now safe to replace
// the generated mirror and search index.
await rm(outputDirectory, { recursive: true, force: true });
await mkdir(outputDirectory, { recursive: true });
const manifestFiles = [];
const searchIndex = [];

for (const { name, content, article } of sourceEntries) {
  const outputPath = path.join(outputDirectory, name);
  await copyFile(path.join(sourceDirectory, name), outputPath);
  manifestFiles.push({
    path: name,
    sha256: createHash("sha256").update(content).digest("hex"),
  });
  searchIndex.push({
    type: "article",
    ...article,
    href: "/articles/" + article.id + "/",
  });
}

const commit = process.env.SOURCE_COMMIT || process.env.COMMIT_REF || execFileSync(
  "git", ["rev-parse", "HEAD"], { cwd: repositoryRoot, encoding: "utf8" },
).trim();
const manifest = {
  repository: "https://github.com/mojtaba-arvin/django-api-versioning",
  source_directory: "docs/articles",
  commit,
  files: manifestFiles,
};
const generatedDirectory = path.join(websiteRoot, "src", "data", "generated");
await mkdir(generatedDirectory, { recursive: true });
await writeFile(path.join(generatedDirectory, "search-index.json"), JSON.stringify(searchIndex, null, 2) + "\n");
await writeFile(path.join(outputDirectory, "_source.json"), JSON.stringify(manifest, null, 2) + "\n");
console.log("[articles] copied " + sourceFiles.length + " canonical articles at " + commit.slice(0, 7) + ".");
console.log("[articles] generated " + searchIndex.length + " search entries.");
