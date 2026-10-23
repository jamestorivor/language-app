import type { selectionData } from "./shadow_root_components/Panel";

// These types also in background.ts might be better to have a file for all schemas
type ParseJapaneseMessage = {
  type: "PARSE_JAPANESE";
  text: string;
};
const PARSE_JAPANESE_MESSAGE_TYPE = "PARSE_JAPANESE";

type JapaneseToken = {
  text: string;
  dictionary_form: string;
  katakana_reading: string;
  start_idx: number;
  end_idx: number;
};

type ParseJapaneseResponse =
  | { ok: true; tokens: JapaneseToken[] }
  | { ok: false; error: string };

function findTextNodes() {
  const APP_TAGS = "vocab_popup";
  const SELECTORS_TO_SKIP =
    "script , style, noscript, textarea, input, [contenteditable]," + APP_TAGS;

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

function wrapWord(textNode: Text, start_idx: number, end_idx: number) {
  const range = document.createRange();
  range.setStart(textNode, start_idx);
  range.setEnd(textNode, end_idx);

  // Creation of the span
  const span = document.createElement("span");

  span.classList.add("vocab-word");
  // creating custom html attribute
  span.dataset.vocabWord = "true";

  range.surroundContents(span);

  return span;
}

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

async function parsePageOnLoad() {
  injectWordStyles();
  const textNodes: Text[] = findTextNodes();

  let response: ParseJapaneseResponse;

  for (const textNode of textNodes) {
    const nodeText = textNode.data;
    try {
      response = await browser.runtime.sendMessage({
        type: PARSE_JAPANESE_MESSAGE_TYPE,
        text: nodeText,
      });

      if (response.ok) {
        console.log({
          input: nodeText,
          tokens: response.tokens,
        });
        let remainingNode: Text = textNode;

        for (const token of response.tokens) {
          let textStartIdx = 0;
          let textEndIdx = token.end_idx - token.start_idx;
          const span = wrapWord(remainingNode, textStartIdx, textEndIdx);

          span.style.cursor = "pointer";

          span.addEventListener("click", () => {
            document.dispatchEvent(
              new CustomEvent("vocab-word-click", {
                detail: {
                  selectedText: token.text,
                  rect: span.getBoundingClientRect(),
                },
              }),
            );
          });

          const remainder = span.nextSibling;

          if (!(remainder instanceof Text)) {
            break;
          }

          remainingNode = remainder;
        }
      } else if (!response.ok) {
        throw new Error(response.error);
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      console.error(message);
    }
  }
}

export { parsePageOnLoad };
