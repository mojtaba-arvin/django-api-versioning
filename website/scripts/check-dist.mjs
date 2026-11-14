#!/usr/bin/env node
/** Validate a built Astro artifact without relying on a hosting provider. */
import { access, readFile, readdir } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const websiteRoot = path.resolve(scriptDirectory, "..");
const defaultDist = path.join(websiteRoot, "dist");

function normalizeBasePath(value = "/") {
  const parts = value.split("/").filter(Boolean);
  return parts.length ? `/${parts.join("/")}/` : "/";
}

async function htmlFiles(directory, prefix = "") {
  const entries = await readdir(directory, { withFileTypes: true });
  const files = [];
  for (const entry of entries) {
    const relative = path.posix.join(prefix, entry.name);
    const absolute = path.join(directory, entry.name);
    if (entry.isDirectory()) files.push(...await htmlFiles(absolute, relative));
    else if (entry.isFile() && entry.name.endsWith(".html")) files.push(relative);
  }
  return files;
}

async function exists(file) {
  try { await access(file); return true; } catch { return false; }
}

/** Return broken local href/src references in generated HTML pages. */
export async function findBrokenLocalReferences(distRoot, basePath = "/") {
  const base = normalizeBasePath(basePath);
  const basePrefix = base === "/" ? "/" : base;
  const pages = await htmlFiles(distRoot);
  const issues = [];

  for (const relativePage of pages) {
    const html = await readFile(path.join(distRoot, relativePage), "utf8");
    const attributes = html.matchAll(/\b(?:href|src)\s*=\s*(["'])(.*?)\1/gs);
    for (const match of attributes) {
      const raw = match[2].trim();
      if (!raw || /^(?:#|[a-z][a-z0-9+.-]*:|\/\/)/i.test(raw)) continue;
      let url;
      try {
        url = new URL(raw, `https://static.invalid${base}${relativePage}`);
      } catch {
        issues.push(`${relativePage}: invalid URL ${JSON.stringify(raw)}`);
        continue;
      }
      if (url.origin !== "https://static.invalid") continue;
      let pathname;
      try { pathname = decodeURIComponent(url.pathname); }
      catch {
        issues.push(`${relativePage}: malformed URL encoding in ${JSON.stringify(raw)}`);
        continue;
      }
      if (!pathname.startsWith(basePrefix)) {
        issues.push(`${relativePage}: local URL escapes configured base path: ${raw}`);
        continue;
      }
      let relativeTarget = pathname.slice(basePrefix.length);
      if (!relativeTarget) relativeTarget = "index.html";
      let target = path.resolve(distRoot, ...relativeTarget.split("/"));
      if (pathname.endsWith("/") || !path.extname(target)) target = path.join(target, "index.html");
      if (!target.startsWith(path.resolve(distRoot) + path.sep) && target !== path.join(path.resolve(distRoot), "index.html")) {
        issues.push(`${relativePage}: URL resolves outside dist: ${raw}`);
      } else if (!await exists(target)) {
        issues.push(`${relativePage}: missing local target for ${raw} (expected ${path.relative(distRoot, target)})`);
      }
    }
  }
  return issues;
}

export async function validateDist(distRoot = defaultDist, basePath = process.env.PUBLIC_BASE_PATH ?? "/") {
  const required = [
    "index.html",
    "404.html",
    "articles/index.html",
    "explorer/index.html",
    "evidence/index.html",
    "data/routes.json",
    "data/check_versions_output.txt",
  ];
  const missing = [];
  for (const relative of required) {
    if (!await exists(path.join(distRoot, relative))) missing.push(relative);
  }
  if (missing.length) throw new Error(`Missing required build output: ${missing.join(", ")}`);

  const routes = JSON.parse(await readFile(path.join(distRoot, "data/routes.json"), "utf8"));
  if (routes.schema_version !== 1 || Object.keys(routes.scenarios ?? {}).length !== 18) {
    throw new Error("Built route evidence has an unsupported schema or scenario count.");
  }
  if (!/^[a-f0-9]{40}$/.test(routes.source?.commit ?? "")) {
    throw new Error("Built route evidence does not contain a full source commit.");
  }

  const homepage = await readFile(path.join(distRoot, "index.html"), "utf8");
  const sections = [
    "what-it-is", "problem", "endpoint-example", "check-versions",
    "segment-point", "lifecycle", "capabilities", "drf-boundaries",
    "limitations", "quick-start",
  ];
  const missingSections = sections.filter((id) => !new RegExp(`id=["']${id}["']`).test(homepage));
  if (missingSections.length) {
    throw new Error(`Homepage is missing required sections: ${missingSections.join(", ")}`);
  }

  const articlePages = (await htmlFiles(path.join(distRoot, "articles")))
    .filter((file) => file !== "index.html" && file.endsWith("/index.html"));
  if (articlePages.length < 25) {
    throw new Error(`Expected at least 25 generated article pages; found ${articlePages.length}.`);
  }

  const broken = await findBrokenLocalReferences(distRoot, basePath);
  if (broken.length) {
    throw new Error(`Found ${broken.length} broken local reference(s):\n- ${broken.join("\n- ")}`);
  }

  console.log(`[dist] verified ${articlePages.length} article pages, 18 evidence scenarios, and local links (${normalizeBasePath(basePath)}).`);
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  validateDist().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
  });
}
