/**
 * Validate the canonical article front matter before it is mirrored into the
 * website. Keep this parser deliberately limited to the repository's
 * documented, flat scalar/list front-matter contract.
 */

function fail(fileName, message) {
  throw new Error(fileName + ": " + message);
}

function unquote(value) {
  const raw = value.trim();
  if (raw.startsWith('"') && raw.endsWith('"')) {
    try {
      return JSON.parse(raw);
    } catch {
      return raw.slice(1, -1);
    }
  }
  if (raw.startsWith("'") && raw.endsWith("'")) {
    return raw.slice(1, -1).replace(/''/g, "'");
  }
  return raw;
}

function scalar(block, key) {
  const match = new RegExp("^[ \\t]*" + key + ":\\s*(.*)$", "m").exec(block);
  return match ? unquote(match[1]) : "";
}

function nestedBlock(frontMatter, key) {
  return new RegExp(
    "^" + key + ":\\s*\\n((?:[ \\t]+[^\\n]*(?:\\n|$))*)",
    "m",
  ).exec(frontMatter)?.[1] ?? "";
}

function listValues(frontMatter, key) {
  const block = nestedBlock(frontMatter, key);
  return block
    .split("\\n")
    .map((line) => {
      const match = /^[ \\t]+-\\s*(.*)$/.exec(line);
      return match ? unquote(match[1]) : "";
    })
    .filter(Boolean);
}

/**
 * Parse and validate one canonical Markdown article.
 *
 * @returns {{ id: string, title: string, description: string, slug: string, keywords: string[] }}
 */
export function parseArticleMetadata(fileName, source) {
  const id = fileName.replace(/\\.md$/, "");
  if (!/^\\d{3}-[a-z0-9]+(?:-[a-z0-9]+)*$/.test(id)) {
    fail(fileName, "file name must start with a three-digit article ID and use lowercase hyphenated words");
  }

  const text = Buffer.isBuffer(source) ? source.toString("utf8") : String(source);
  const match = /^---\\s*\\n([\\s\\S]*?)\\n---(?:\\s*\\n|$)/.exec(text);
  if (!match) fail(fileName, "missing or malformed YAML front matter");

  const frontMatter = match[1];
  const body = text.slice(match[0].length);
  const title = scalar(frontMatter, "title");
  const description = scalar(frontMatter, "description");
  const slug = scalar(frontMatter, "slug");
  const author = nestedBlock(frontMatter, "author");
  const authorName = scalar(author, "name");
  const authorUrl = scalar(author, "url");
  const keywords = listValues(frontMatter, "keywords");

  if (!title) fail(fileName, "title is required");
  if (title.length > 70) fail(fileName, "title must be 70 characters or fewer");
  if (!description) fail(fileName, "description is required");
  if (description.length > 160) fail(fileName, "description must be 160 characters or fewer");
  if (!/^\\d{3}-[a-z0-9]+(?:-[a-z0-9]+)*$/.test(slug) || slug.length > 100) {
    fail(fileName, "slug must be a lowercase hyphenated value of at most 100 characters and retain the article ID");
  }
  if (!slug.startsWith(id.slice(0, 3) + "-")) {
    fail(fileName, "slug numeric prefix must match the article file ID");
  }

  const h1 = /^#\\s+(.+?)\\s*$/m.exec(body)?.[1];
  if (h1 !== title) fail(fileName, "the first H1 must match the front-matter title exactly");

  if (authorName !== "Mojtaba Arvin") {
    fail(fileName, 'author.name must be "Mojtaba Arvin"');
  }
  if (authorUrl !== "https://www.linkedin.com/in/mojtabaarvin/") {
    fail(fileName, "author.url must use the canonical LinkedIn profile URL");
  }

  if (keywords.length < 2 || keywords.length > 5) {
    fail(fileName, "keywords must contain between 2 and 5 entries");
  }
  const longKeyword = keywords.find((keyword) => keyword.length > 40);
  if (longKeyword) {
    fail(fileName, 'keyword "' + longKeyword + '" exceeds 40 characters');
  }

  return { id, title, description, slug, keywords };
}
