import { findTextNodes } from "@/features/vocabulary/text-nodes";
import { applyClickableWordToNode } from "@/features/vocabulary/bound-words";
import { requestJapaneseParsing } from "@/api/parse-japanese";

function injectWordStyles() {
  if (document.getElementById("vocab-word-styles")) return;

  const style = document.createElement("style");
  style.id = "vocab-word-styles";
  style.textContent = `
    .vocab-word {
      border-bottom: 2px solid orange;
    }

    .vocab-word:hover {
      background-color: rgb(255 165 0 / 15%);
    }
  `;
  document.head.appendChild(style);
}

async function processPageText() {
  const textNodes: Text[] = findTextNodes();
  for (const textNode of textNodes) {
    const nodeText = textNode.data;
    try {
      const response = await requestJapaneseParsing(nodeText);
      const tokens = response.tokens;
      applyClickableWordToNode(tokens, textNode);
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      console.error(message);
    }
  }
}

async function parsePageOnLoad() {
  injectWordStyles();
  await processPageText();
}

export { parsePageOnLoad };
