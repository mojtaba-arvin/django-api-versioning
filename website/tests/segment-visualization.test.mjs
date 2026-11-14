import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

const components = path.join(process.cwd(), "src", "components");
const modelLabel =
  "routing model / explanatory visualization, not actual Python execution";

test("Segment Diagram carries the required explanatory-model label", async () => {
  const source = await readFile(path.join(components, "SegmentDiagram.astro"), "utf8");
  assert.ok(source.includes(modelLabel));
  assert.match(source, /segments\.map/);
});

test("Segment Explorer labels the model and keeps a server-rendered fallback", async () => {
  const source = await readFile(path.join(components, "SegmentExplorer.astro"), "utf8");
  assert.ok(source.includes(modelLabel));
  assert.match(source, /<SegmentDiagram scenario=/);
  assert.match(source, /<noscript>/);
  assert.match(source, /initial\.question/);
  assert.match(source, /initialRoute/);
});
