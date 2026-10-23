const APP_TAGS = "vocab_popup";
const SELECTORS_TO_SKIP =
  "script , style, noscript, textarea, input, [contenteditable]," + APP_TAGS;

function findTextNodes() {
  const walker = document.createTreeWalker(
    document.body,
    NodeFilter.SHOW_TEXT,
    {
      acceptNode(node) {
        const parent = node.parentElement;

        if (!parent || parent.closest(SELECTORS_TO_SKIP)) {
          return NodeFilter.FILTER_REJECT;
        }

        return node.textContent?.trim()
          ? NodeFilter.FILTER_ACCEPT
          : NodeFilter.FILTER_REJECT;
      },
    },
  );

  const textNodes: Text[] = [];
  let node: Node | null = walker.nextNode();
  while (node !== null) {
    textNodes.push(node as Text);
    node = walker.nextNode();
  }

  return textNodes;
}

export { findTextNodes };
