#!/usr/bin/env node
/**
 * Copy the canonical repository article corpus into Astro's generated content
 * directory. The source of truth is ../docs/articles; no remote fetch occurs.
 */
import { createHash } from "node:crypto";
import { execFileSync } from "node:child_process";
import { copyFile, mkdir, readFile, readdir, rm, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const websiteRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const repositoryRoot = path.resolve(websiteRoot, "..");
const sourceDirectory = path.join(repositoryRoot, "docs", "articles");
const outputDirectory = path.join(websiteRoot, "src", "content", "articles");

const sourceEntries = await readdir(sourceDirectory, { withFileTypes: true });
const sourceFiles = sourceEntries
  .filter((entry) => entry.isFile() && entry.name.endsWith(".md"))
  .map((entry) => entry.name)
  .sort();

if (sourceFiles.length === 0) {
  throw new Error(`No Markdown articles found in ${path.relative(repositoryRoot, sourceDirectory)}.`);
}

await mkdir(outputDirectory, { recursive: true });
const existingEntries = await readdir(outputDirectory, { withFileTypes: true });
for (const entry of existingEntries) {
  if (entry.isFile() && entry.name.endsWith(".md") && !sourceFiles.includes(entry.name)) {
    await rm(path.join(outputDirectory, entry.name));
  }
}

const manifestFiles = [];
for (const name of sourceFiles) {
  const sourcePath = path.join(sourceDirectory, name);
  const outputPath = path.join(outputDirectory, name);
  const content = await readFile(sourcePath);
  await copyFile(sourcePath, outputPath);
  manifestFiles.push({
    path: name,
    sha256: createHash("sha256").update(content).digest("hex"),
  });
}

const commit =
  process.env.SOURCE_COMMIT ||
  process.env.COMMIT_REF ||
  execFileSync("git", ["rev-parse", "HEAD"], {
    cwd: repositoryRoot,
    encoding: "utf8",
  }).trim();

const manifest = {
  repository: "https://github.com/mojtaba-arvin/django-api-versioning",
  source_directory: "docs/articles",
  commit,
  files: manifestFiles,
};

function scalar(frontMatter, key) {
  const match = new RegExp(`^${key}:\\s*(?:"([^"]*)"|'([^']*)'|([^\\n]+))#!/usr/bin/env node
/**
 * Copy the canonical repository article corpus into Astro's generated content
 * directory. The source of truth is ../docs/articles; no remote fetch occurs.
 */
import { createHash } from "node:crypto";
import { execFileSync } from "node:child_process";
import { copyFile, mkdir, readFile, readdir, rm, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const websiteRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const repositoryRoot = path.resolve(websiteRoot, "..");
const sourceDirectory = path.join(repositoryRoot, "docs", "articles");
const outputDirectory = path.join(websiteRoot, "src", "content", "articles");

const sourceEntries = await readdir(sourceDirectory, { withFileTypes: true });
const sourceFiles = sourceEntries
  .filter((entry) => entry.isFile() && entry.name.endsWith(".md"))
  .map((entry) => entry.name)
  .sort();

if (sourceFiles.length === 0) {
  throw new Error(`No Markdown articles found in ${path.relative(repositoryRoot, sourceDirectory)}.`);
}

await mkdir(outputDirectory, { recursive: true });
const existingEntries = await readdir(outputDirectory, { withFileTypes: true });
for (const entry of existingEntries) {
  if (entry.isFile() && entry.name.endsWith(".md") && !sourceFiles.includes(entry.name)) {
    await rm(path.join(outputDirectory, entry.name));
  }
}

const manifestFiles = [];
for (const name of sourceFiles) {
  const sourcePath = path.join(sourceDirectory, name);
  const outputPath = path.join(outputDirectory, name);
  const content = await readFile(sourcePath);
  await copyFile(sourcePath, outputPath);
  manifestFiles.push({
    path: name,
    sha256: createHash("sha256").update(content).digest("hex"),
  });
}

const commit =
  process.env.SOURCE_COMMIT ||
  process.env.COMMIT_REF ||
  execFileSync("git", ["rev-parse", "HEAD"], {
    cwd: repositoryRoot,
    encoding: "utf8",
  }).trim();

, "m").exec(frontMatter);
  return match?.[1] ?? match?.[2] ?? match?.[3]?.trim() ?? "";
}

function articleSearchEntry(name, content) {
  const frontMatter = content.toString("utf8").split(/^---\\s*$/m)[1] ?? "";
  const keywordBlock = /^keywords:\\s*\\n((?:[ \\t]+-\\s*.*(?:\\n|$))*)/m.exec(frontMatter)?.[1] ?? "";
  const keywords = [...keywordBlock.matchAll(/^\\s+-\\s*(?:"([^"]*)"|'([^']*)'|(.+))$/gm)]
    .map((match) => (match[1] ?? match[2] ?? match[3] ?? "").trim())
    .filter(Boolean);
  const id = name.replace(/\\.md$/, "");
  return {
    type: "article",
    id,
    title: scalar(frontMatter, "title") || id,
    description: scalar(frontMatter, "description"),
    slug: scalar(frontMatter, "slug"),
    keywords,
    href: `/articles/${id}/`,
  };
}

const searchIndex = [];
for (const name of sourceFiles) {
  const content = await readFile(path.join(sourceDirectory, name));
  searchIndex.push(articleSearchEntry(name, content));
}
const generatedDirectory = path.join(websiteRoot, "src", "data", "generated");
await mkdir(generatedDirectory, { recursive: true });
await writeFile(
  path.join(generatedDirectory, "search-index.json"),
  JSON.stringify(searchIndex, null, 2) + "\\n",
);

await writeFile(
  path.join(outputDirectory, "_source.json"),
  JSON.stringify(manifest, null, 2) + "\n",
);

console.log(
  `[articles] copied ${sourceFiles.length} canonical Markdown files from docs/articles at ${commit.slice(0, 7)}.`,
);
