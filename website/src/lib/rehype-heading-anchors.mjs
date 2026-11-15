import { visit } from "unist-util-visit";

/**
 * Add accessible, keyboard-focusable deep links to article headings.
 * The visible marker is decorative; the anchor has an explicit accessible name.
 */
export function rehypeHeadingAnchors() {
  return (tree) => {
    visit(tree, "element", (node) => {
      if (!/^h[2-6]$/.test(node.tagName ?? "")) return;
      const id = node.properties?.id;
      if (typeof id !== "string" || !id) return;
      const existing = Array.isArray(node.properties.className)
        ? node.properties.className
        : typeof node.properties.className === "string"
          ? [node.properties.className]
          : [];
      node.properties.className = [...existing, "has-anchor"];
      node.children.push({
        type: "element",
        tagName: "a",
        properties: {
          href: "#" + id,
          className: ["heading-anchor"],
          ariaLabel: "Link to this section",
          title: "Link to this section",
        },
        children: [{ type: "text", value: "#" }],
      });
    });
  };
}
