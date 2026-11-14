#!/usr/bin/env node
/** Copy canonical Markdown articles and generate the static search index. */
import { createHash } from "node:crypto";
import { execFileSync } from "node:child_process";
import { copyFile, mkdir, readFile, readdir, rm, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const websiteRoot = path.resolve(scriptDirectory, "..");
const repositoryRoot = path.resolve(websiteRoot, "..");
const sourceDirectory = path.join(repositoryRoot, "docs", "articles");
const outputDirectory = path.join(websiteRoot, "src", "content", "articles");
const sourceFiles = (await readdir(sourceDirectory))
  .filter((name) => name.endsWith(".md"))
  .sort((a, b) => a.localeCompare(b, "en", { numeric: true }));
if (!sourceFiles.length) throw new Error("No canonical Markdown articles found in docs/articles.");

await rm(outputDirectory, { recursive: true, force: true });
await mkdir(outputDirectory, { recursive: true });
const manifestFiles = [];
const searchIndex = [];

function scalar(frontMatter, key) {
  const raw = new RegExp("^" + key + ":\\s*(.*)$", "m").exec(frontMatter)?.[1]?.trim() ?? "";
  return raw.replace(/^['\"]|['\"]$/g, "");
}

function articleSearchEntry(name, content) {
  const text = content.toString("utf8");
  const frontMatter = /^---\s*\n([\s\S]*?)\n---(?:\s|$)/.exec(text)?.[1] ?? "";
  const id = name.replace(/\.md$/, "");
  const title = scalar(frontMatter, "title");
  const description = scalar(frontMatter, "description");
  const slug = scalar(frontMatter, "slug");
  if (!title || !description || !slug) {
    throw new Error("Article " + name + " is missing title, description or slug front matter.");
  }
  const keywordBlock = /^keywords:\s*\n((?:[ \t]+-\s*.*(?:\n|$))*)/m.exec(frontMatter)?.[1] ?? "";
  const keywords = keywordBlock
    .split("\n")
    .map((line) => line.replace(/^\s*-\s*/, "").trim().replace(/^['\"]|['\"]$/g, ""))
    .filter(Boolean);
  return { type: "article", id, title, description, slug, keywords, href: "/articles/" + id + "/" };
}

for (const name of sourceFiles) {
  const sourcePath = path.join(sourceDirectory, name);
  const outputPath = path.join(outputDirectory, name);
  const content = await readFile(sourcePath);
  await copyFile(sourcePath, outputPath);
  manifestFiles.push({ path: name, sha256: createHash("sha256").update(content).digest("hex") });
  searchIndex.push(articleSearchEntry(name, content));
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
