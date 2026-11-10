import { findTextNodes } from "@/features/vocabulary/text-nodes";
import { applyClickableWordToNode } from "@/features/vocabulary/bound-words";
import { requestJapaneseParsing } from "@/messaging/parse-japanese";
import type { TokenGroup } from "@/contracts/parse-japanese";

function injectWordStyles() {
  if (document.getElementById("vocab-word-styles")) return;

  const style = document.createElement("style");
  style.id = "vocab-word-styles";
  style.textContent = `
    .vocab-word {
      cursor: pointer;
    }

    .vocab-word:is(.unfamiliar, .familiarity-1, .familiarity-2, .familiarity-3, .familiarity-4) {
      border-bottom: 1px solid rgb(var(--vocab-accent));
      background-color: rgb(var(--vocab-accent) / 24%);
      border-radius: 5px;
      padding: 1px 2px;
      -webkit-box-decoration-break: clone;
      box-decoration-break: clone;
    }

    /* Unfamiliar (0) — rose */
    .vocab-word.unfamiliar {
      --vocab-accent: 192 76 116;
    }

    /* 1 — tangerine */
    .vocab-word.familiarity-1 {
      --vocab-accent: 224 105 48;
    }

    /* 2 — gold */
    .vocab-word.familiarity-2 {
      --vocab-accent: 235 176 30;
    }

    /* 3 — blue */
    .vocab-word.familiarity-3 {
      --vocab-accent: 35 138 225;
    }

    /* 4 — teal */
    .vocab-word.familiarity-4 {
      --vocab-accent: 20 198 163;
    }

    .vocab-word:is(.unfamiliar, .familiarity-1, .familiarity-2, .familiarity-3, .familiarity-4):hover {
      background-color: rgb(var(--vocab-accent) / 34%);
    }
  `;
  document.head.appendChild(style);
}

async function processPageText(language: "ja" | "en") {
  const textNodes: Text[] = findTextNodes();
  let tokenList: TokenGroup[] = [];
  for (const textNode of textNodes) {
    const nodeText = textNode.data;
    try {
      const response = await requestJapaneseParsing(nodeText, language);
      const tokens = response.response;
      tokenList.push(...tokens);
      applyClickableWordToNode(tokens, textNode);
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      throw new Error(`Could not parse this page: ${message}`);
    }
  }
  console.log(`complete tokenlist len: ${tokenList.length}`);
  return tokenList;
}

async function parsePageOnLoad(language: "ja" | "en" = "ja") {
  injectWordStyles();
  return await processPageText(language);
}

export { parsePageOnLoad };
