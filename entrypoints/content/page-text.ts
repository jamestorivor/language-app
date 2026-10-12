function handleTextSelection(): void {
  const selection: Selection | null = window.getSelection();

  if (selection) {
    const selectedText: string = selection.toString().trim();
    if (selectedText.length > 0) {
      console.log(selectedText);
    }
  } else if (!selection) {
    console.log("Nothing selected");
  } else {
    console.log("Error");
  }
}

export default handleTextSelection;
