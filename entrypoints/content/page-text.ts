function getSelectedText(): string {
  const selection: Selection | null = window.getSelection();

  if (selection) {
    const selectedText: string = selection.toString().trim();
    if (selectedText.length > 0) {
      return selectedText;
    }
  }
  return "";
}

export default getSelectedText;
