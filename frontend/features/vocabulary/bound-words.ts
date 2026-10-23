import type { TokenGroup } from "@/contracts/parse-japanese";

function wrapWordWithSpan(textNode: Text, start_idx: number, end_idx: number) {
  const range = document.createRange();
  range.setStart(textNode, start_idx);
  range.setEnd(textNode, end_idx);

  // Creation of the span
  const span = document.createElement("span");

  span.style.cursor = "pointer";

  span.classList.add("vocab-word");
  // creating custom html attribute
  span.dataset.vocabWord = "true";

  range.surroundContents(span);

  return span;
}

function applyClickableWord(token: TokenGroup, textNode: Text) {
  let textStartIdx = 0;
  let textEndIdx = token.text.length;
  const span = wrapWordWithSpan(textNode, textStartIdx, textEndIdx);

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
  return span;
}

function applyClickableWordToNode(tokens: TokenGroup[], textNode: Text) {
  let remainingNode: Text = textNode;

  for (const token of tokens) {
    const span = applyClickableWord(token, remainingNode);

    const remainder = span.nextSibling;

    if (!(remainder instanceof Text)) {
      break;
    }

    remainingNode = remainder;
  }
}

export { applyClickableWordToNode };
