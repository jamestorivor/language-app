import type { selectionData } from "./Panel";

function handleTextSelection(): selectionData | null {
  const selection: Selection | null = window.getSelection();

  if (!selection) {
    return null;
  }

  const selectedText: string = selection.toString().trim();
  if (selectedText.length < 1) {
    return null;
  }
  const range = selection.getRangeAt(0);
  const rect = range.getBoundingClientRect();
  return {
    selectedText: selectedText,
    rect: rect,
  };
}

export default handleTextSelection;
