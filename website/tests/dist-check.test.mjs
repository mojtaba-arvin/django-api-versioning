import assert from "node:assert/strict";
import { mkdtemp, mkdir, rm, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { findBrokenLocalReferences } from "../scripts/check-dist.mjs";

async function fixture(t) {
  const root = await mkdtemp(path.join(os.tmpdir(), "dav-dist-"));
  t.after(() => rm(root, { recursive: true, force: true }));
  await mkdir(path.join(root, "assets"), { recursive: true });
  await writeFile(path.join(root, "index.html"), '<a href="/articles/">Articles</a><script src="/assets/site.js"></script>');
  await writeFile(path.join(root, "assets/site.js"), "");
  await mkdir(path.join(root, "articles"), { recursive: true });
  await writeFile(path.join(root, "articles/index.html"), "<h1>Articles</h1>");
  return root;
}

test("static reference checker accepts valid root-relative links", async (t) => {
  const root = await fixture(t);
  assert.deepEqual(await findBrokenLocalReferences(root, "/"), []);
});

test("static reference checker reports missing local files", async (t) => {
  const root = await fixture(t);
  await writeFile(path.join(root, "index.html"), '<a href="/missing/">Missing</a>');
  const issues = await findBrokenLocalReferences(root, "/");
  assert.equal(issues.length, 1);
  assert.match(issues[0], /missing\/index\.html/);
});

test("static reference checker enforces a project-site base path", async (t) => {
  const root = await fixture(t);
  const issues = await findBrokenLocalReferences(root, "/django-api-versioning/");
  assert.equal(issues.length, 2);
  assert.ok(issues.every((issue) => issue.includes("escapes configured base path")));
});
