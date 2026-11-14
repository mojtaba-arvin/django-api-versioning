import assert from "node:assert/strict";
import test from "node:test";
import { rehypeHeadingAnchors } from "../src/lib/rehype-heading-anchors.mjs";

test("heading anchors preserve existing classes and expose an accessible name", () => {
  const heading = {
    type: "element",
    tagName: "h2",
    properties: { id: "segment-point", className: "section-title" },
    children: [{ type: "text", value: "Segment Point" }],
  };
  const tree = { type: "root", children: [heading] };
  rehypeHeadingAnchors()(tree);
  assert.deepEqual(heading.properties.className, ["section-title", "has-anchor"]);
  const anchor = heading.children.at(-1);
  assert.equal(anchor.tagName, "a");
  assert.equal(anchor.properties.href, "#segment-point");
  assert.equal(anchor.properties.ariaLabel, "Link to this section");
});

test("heading anchors do not alter H1 page titles", () => {
  const heading = { type: "element", tagName: "h1", properties: { id: "page-title" }, children: [] };
  rehypeHeadingAnchors()({ type: "root", children: [heading] });
  assert.equal(heading.children.length, 0);
});
