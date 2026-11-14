import { visit } from "unist-util-visit";

const text = (node) =>
  node.type === "text" ? node.value : (node.children ?? []).map(text).join("");

/** Appends a visible, keyboard-focusable "#" link to h2–h4 that have ids. */
export function rehypeHeadingAnchors() {
  return (tree) => {
    visit(tree, "element", (node) => {
      if (!/^h[2-4]$/.test(node.tagName) || !node.properties?.id) return;
      const label = text(node).trim();
      node.properties.className = [...(node.properties.className ?? []), "has-anchor"];
      node.children.push({
        type: "element",
        tagName: "a",
        properties: { className: ["heading-anchor"], href: `#${node.properties.id}` },
        children: [
          { type: "element", tagName: "span", properties: { ariaHidden: "true" }, children: [{ type: "text", value: "#" }] },
          { type: "element", tagName: "span", properties: { className: ["sr-only"] }, children: [{ type: "text", value: `Link to section: ${label}` }] },
        ],
      });
    });
  };
}