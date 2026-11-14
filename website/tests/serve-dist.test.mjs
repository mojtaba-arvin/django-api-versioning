import assert from "node:assert/strict";
import { mkdtemp, mkdir, rm, symlink, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { resolveStaticFile } from "../src/lib/static-path.mjs";

async function fixture(t) {
  const root = await mkdtemp(path.join(os.tmpdir(), "dav-static-"));
  const outside = await mkdtemp(path.join(os.tmpdir(), "dav-outside-"));
  t.after(async () => {
    await rm(root, { recursive: true, force: true });
    await rm(outside, { recursive: true, force: true });
  });
  await mkdir(path.join(root, "assets"), { recursive: true });
  await mkdir(path.join(root, "articles", "intro"), { recursive: true });
  await writeFile(path.join(root, "index.html"), "home");
  await writeFile(path.join(root, "assets", "site.js"), "asset");
  await writeFile(path.join(root, "articles", "intro", "index.html"), "article");
  await writeFile(path.join(outside, "secret.txt"), "secret");
  await symlink(outside, path.join(root, "external-link"), "dir");
  return root;
}

test("static server resolves project-site root and nested files", async (t) => {
  const root = await fixture(t);
  assert.equal(await resolveStaticFile(root, "/project/", "/project"), path.join(root, "index.html"));
  assert.equal(await resolveStaticFile(root, "/project/articles/intro/", "/project"), path.join(root, "articles", "intro", "index.html"));
  assert.equal(await resolveStaticFile(root, "/project/assets/site.js", "/project"), path.join(root, "assets", "site.js"));
});

test("static server rejects requests outside the configured base path", async (t) => {
  const root = await fixture(t);
  assert.equal(await resolveStaticFile(root, "/", "/project"), null);
  assert.equal(await resolveStaticFile(root, "/project-elsewhere/", "/project"), null);
  assert.equal(await resolveStaticFile(root, "/assets/site.js", "/project"), null);
});

test("static server rejects traversal and symlink escapes", async (t) => {
  const root = await fixture(t);
  assert.equal(await resolveStaticFile(root, "/project/%2e%2e/secret.txt", "/project"), null);
  assert.equal(await resolveStaticFile(root, "/project/external-link/secret.txt", "/project"), null);
});

test("static server supports root-hosted output", async (t) => {
  const root = await fixture(t);
  assert.equal(await resolveStaticFile(root, "/", "/"), path.join(root, "index.html"));
  assert.equal(await resolveStaticFile(root, "/assets/site.js", "/"), path.join(root, "assets", "site.js"));
});
