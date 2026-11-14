import assert from "node:assert/strict";
import test from "node:test";

import { resolveArticleLink } from "../src/lib/article-index.mjs";

test("exact file identity takes precedence over an earlier matching slug", () => {
  const articles = [
    { id: "001-first", slug: "second" },
    { id: "002-second", slug: "second" },
  ];

  assert.equal(resolveArticleLink("/002-second/", articles), "002-second");
});

test("ambiguous exact slugs do not silently select the first article", () => {
  const articles = [
    { id: "001-first", slug: "shared-topic" },
    { id: "002-second", slug: "shared-topic" },
  ];

  assert.equal(resolveArticleLink("/shared-topic/", articles), null);
});

test("ambiguous numeric-prefix-free file identities are rejected", () => {
  const articles = [
    { id: "001-shared-topic", slug: "first" },
    { id: "002-shared-topic", slug: "second" },
  ];

  assert.equal(resolveArticleLink("/shared-topic/", articles), null);
});

test("a fuzzy match is accepted only when the best candidate is unique", () => {
  const articles = [
    { id: "001-foo-bar-one", slug: "foo-bar-one" },
    { id: "002-foo-baz-two", slug: "foo-baz-two" },
  ];

  assert.equal(resolveArticleLink("/foo-bar-baz/", articles), null);
});

test("a unique fuzzy match remains resolvable", () => {
  const articles = [
    { id: "001-foo-bar", slug: "foo-bar" },
    { id: "002-unrelated", slug: "unrelated-topic" },
  ];

  assert.equal(resolveArticleLink("/foo-bar-extra/", articles), "001-foo-bar");
});

test("query strings and fragments do not change the target article", () => {
  const articles = [{ id: "001-guide", slug: "guide" }];

  assert.equal(resolveArticleLink("/guide/?source=docs#setup", articles), "001-guide");
});
