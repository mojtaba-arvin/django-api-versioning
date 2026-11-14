import { visit } from "unist-util-visit";
import { listArticles, resolveArticleLink } from "./article-index.mjs";

/**
 * - Removes the first H1 (the page layout renders the title).
 * - Rewrites upstream site-relative article links to /articles/<id>/.
 *   Unresolvable relative links are reported and left unchanged.
 */
const rawBase = process.env.PUBLIC_BASE_PATH ?? "/";
const basePrefix =
  rawBase === "/" ? "" : `/${rawBase.split("/").filter(Boolean).join("/")}`;

export function remarkArticleLinks() {
  return (tree, file) => {
    const filePath = String(file.path ?? file.history?.[0] ?? "");
    if (!filePath.includes("content/articles")) return;
    const articles = listArticles();
    const firstH1 = tree.children.findIndex((n) => n.type === "heading" && n.depth === 1);
    if (firstH1 !== -1) tree.children.splice(firstH1, 1);
    visit(tree, "link", (node) => {
      const href = node.url;
      if (!href || /^(https?:|mailto:|#)/.test(href)) return;
      const id = resolveArticleLink(href, articles);
      if (id) {
        const suffixIndex = href.search(/[?#]/);
        const suffix = suffixIndex === -1 ? "" : href.slice(suffixIndex);
        node.url = `${basePrefix}/articles/${id}/${suffix}`;
      } else {
        console.warn(`[articles] unresolved link ${href} in ${filePath}`);
      }
    });
  };
}