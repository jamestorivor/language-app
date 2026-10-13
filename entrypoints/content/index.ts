import handleTextSelection from "./page-text.ts";

export default defineContentScript({
  matches: ["*://*.google.com/*", "http://localhost/*"],
  main() {
    let latestSelectedText = "";
    document.addEventListener("selectionchange", () => {
      const selectedText = handleTextSelection();
      if (selectedText.length > 0) {
        latestSelectedText = selectedText;
      }
    });
    browser.runtime.onMessage.addListener((message, sender, sendResponse) => {
      if (message.type == "GET_SELECTED_TEXT") {
        sendResponse({ success: true, text: latestSelectedText });
      }
    });
  },
});
