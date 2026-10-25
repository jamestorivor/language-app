import type { TokenGroup } from "@/contracts/parse-japanese";

function get_familiarity_css_class(token: TokenGroup) {
  if (token.familiarity_score == 0) {
    return "unfamiliar";
  } else {
    return `familiarity-${token.familiarity_score?.toString()}`;
  }
}

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

  const className = get_familiarity_css_class(token);
  span.className = className;

  span.addEventListener("click", () => {
    document.dispatchEvent(
      new CustomEvent("vocab-word-click", {
        detail: {
          wordToken: token,
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
    let remainder: ChildNode | null;
    if (!token.display) {
      remainder = remainingNode.splitText(token.text.length);
    } else {
      const span = applyClickableWord(token, remainingNode);
      remainder = span.nextSibling;
    }

    if (!(remainder instanceof Text)) {
      break;
    }

    remainingNode = remainder;
  }
}

export { applyClickableWordToNode };
