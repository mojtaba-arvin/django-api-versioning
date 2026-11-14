import assert from "node:assert/strict";
import test from "node:test";
import { listArticles } from "../src/lib/article-index.mjs";

process.env.PUBLIC_BASE_PATH = "/project-docs";
const { remarkArticleLinks } = await import("../src/lib/remark-article-links.mjs?base-path-test");

test("article links preserve query and fragment while respecting the site base path", () => {
  const article = listArticles()[0];
  const link = { type: "link", url: article.slug + "?ref=series#overview", children: [{ type: "text", value: article.title }] };
  const heading = { type: "heading", depth: 1, children: [{ type: "text", value: article.title }] };
  const tree = { type: "root", children: [heading, { type: "paragraph", children: [link] }] };
  remarkArticleLinks()(tree, { path: process.cwd() + "/src/content/articles/" + article.id + ".md" });
  assert.equal(tree.children.length, 1);
  assert.equal(link.url, "/project-docs/articles/" + article.id + "/?ref=series#overview");
});

test("external links are left unchanged", () => {
  const link = { type: "link", url: "https://example.com/docs", children: [{ type: "text", value: "External" }] };
  const tree = { type: "root", children: [{ type: "paragraph", children: [link] }] };
  remarkArticleLinks()(tree, { path: process.cwd() + "/src/content/articles/sample.md" });
  assert.equal(link.url, "https://example.com/docs");
});
