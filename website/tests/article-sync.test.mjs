import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFile, readdir } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

const root = process.cwd();
const entries = JSON.parse(await readFile(path.join(root, "src/data/generated/search-index.json"), "utf8"));
const manifest = JSON.parse(await readFile(path.join(root, "src/content/articles/_source.json"), "utf8"));
const canonicalDirectory = path.resolve(root, "../docs/articles");

test("search index and content mirror cover every canonical article exactly once", async () => {
  const names = (await readdir(canonicalDirectory)).filter((name) => name.endsWith(".md")).sort();
  assert.equal(entries.length, names.length);
  assert.equal(new Set(entries.map((entry) => entry.id)).size, entries.length);
  assert.deepEqual(manifest.files.map((file) => file.path).sort(), names);
  for (const entry of entries) {
    assert.ok(entry.title.length > 0);
    assert.ok(entry.description.length > 0);
    assert.ok(entry.slug.length > 0);
    assert.equal(entry.href, "/articles/" + entry.id + "/");
    const bytes = await readFile(path.join(canonicalDirectory, entry.id + ".md"));
    const hash = createHash("sha256").update(bytes).digest("hex");
    assert.equal(manifest.files.find((file) => file.path === entry.id + ".md")?.sha256, hash);
  }
});
