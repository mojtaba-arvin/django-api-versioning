import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

const root = process.cwd();
const generated = path.join(root, "src", "data", "generated");
const published = path.join(root, "public", "data");

test("public evidence is an exact copy of the committed source evidence", async () => {
  const [sourceRoutes, publicRoutes, sourceOutput, publicOutput] = await Promise.all([
    readFile(path.join(generated, "routes.json"), "utf8"),
    readFile(path.join(published, "routes.json"), "utf8"),
    readFile(path.join(generated, "check_versions_output.txt"), "utf8"),
    readFile(path.join(published, "check_versions_output.txt"), "utf8"),
  ]);
  assert.equal(publicRoutes, sourceRoutes);
  assert.equal(publicOutput, sourceOutput);
  const data = JSON.parse(publicRoutes);
  assert.equal(data.schema_version, 1);
  assert.match(data.source.commit, /^[a-f0-9]{40}$/);
  assert.equal(Object.keys(data.scenarios).length, 18);
  assert.ok(data.source.files.length > 0);
  assert.ok(data.source.evidence_files.length > 0);
});
