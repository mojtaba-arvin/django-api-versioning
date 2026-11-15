import assert from "node:assert/strict";
import test from "node:test";

import { parseArticleMetadata } from "../src/lib/article-metadata.mjs";

function article({
  title = "A focused article title",
  description = "A concise description for a canonical project article.",
  slug = "001-a-focused-article",
  authorName = "Mojtaba Arvin",
  authorUrl = "https://www.linkedin.com/in/mojtabaarvin/",
  keywords = ['"Django API"', '"URL routing"'],
  h1 = title,
} = {}) {
  return `---
slug: "${slug}"
title: "${title}"
description: "${description}"
author:
  name: "${authorName}"
  url: "${authorUrl}"
keywords:
${keywords.map((keyword) => "  - " + keyword).join("\n")}
---

# ${h1}

Article body.
`;
}

test("accepts canonical quoted metadata and returns normalized search fields", () => {
  const parsed = parseArticleMetadata(
    "001-a-focused-article.md",
    article(),
  );

  assert.deepEqual(parsed, {
    id: "001-a-focused-article",
    title: "A focused article title",
    description: "A concise description for a canonical project article.",
    slug: "001-a-focused-article",
    keywords: ["Django API", "URL routing"],
  });
});

test("accepts plain YAML keyword scalars used by older canonical articles", () => {
  const parsed = parseArticleMetadata(
    "001-a-focused-article.md",
    article({ keywords: ["Django REST Framework", "API Versioning"] }),
  );

  assert.deepEqual(parsed.keywords, [
    "Django REST Framework",
    "API Versioning",
  ]);
});

test("rejects missing or malformed front matter", () => {
  assert.throws(
    () => parseArticleMetadata("001-a-focused-article.md", "# Title\n"),
    /missing or malformed YAML front matter/,
  );
});

test("rejects titles longer than 70 characters", () => {
  assert.throws(
    () => parseArticleMetadata(
      "001-a-focused-article.md",
      article({ title: "T".repeat(71) }),
    ),
    /title must be 70 characters or fewer/,
  );
});

test("rejects descriptions longer than 160 characters", () => {
  assert.throws(
    () => parseArticleMetadata(
      "001-a-focused-article.md",
      article({ description: "D".repeat(161) }),
    ),
    /description must be 160 characters or fewer/,
  );
});

test("rejects slugs that do not preserve the article ID", () => {
  assert.throws(
    () => parseArticleMetadata(
      "001-a-focused-article.md",
      article({ slug: "002-a-focused-article" }),
    ),
    /slug numeric prefix must match/,
  );
});

test("rejects a title that differs from the first H1", () => {
  assert.throws(
    () => parseArticleMetadata(
      "001-a-focused-article.md",
      article({ h1: "A different heading" }),
    ),
    /first H1 must match/,
  );
});

test("requires the canonical author identity and profile URL", () => {
  assert.throws(
    () => parseArticleMetadata(
      "001-a-focused-article.md",
      article({ authorName: "Another Author" }),
    ),
    /author.name/,
  );
  assert.throws(
    () => parseArticleMetadata(
      "001-a-focused-article.md",
      article({ authorUrl: "https://example.com/" }),
    ),
    /author.url/,
  );
});

test("requires between two and five keywords", () => {
  for (const keywords of [[], ['"one"'], ['"1"', '"2"', '"3"', '"4"', '"5"', '"6"']]) {
    assert.throws(
      () => parseArticleMetadata(
        "001-a-focused-article.md",
        article({ keywords }),
      ),
      /between 2 and 5/,
    );
  }
});

test("rejects keywords longer than 40 characters", () => {
  assert.throws(
    () => parseArticleMetadata(
      "001-a-focused-article.md",
      article({ keywords: ['"' + "K".repeat(41) + '"', '"Django"'] }),
    ),
    /exceeds 40 characters/,
  );
});

test("rejects file names without a three-digit article ID", () => {
  assert.throws(
    () => parseArticleMetadata("article.md", article()),
    /file name must start with a three-digit article ID/,
  );
});
