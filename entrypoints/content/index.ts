import handleTextSelection from "./page-text.ts";

export default defineContentScript({
  matches: ["*://*.google.com/*", "http://localhost/*"],
  main() {
    document.addEventListener("selectionchange", handleTextSelection);
  },
});
