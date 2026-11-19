/** Character offsets returned by the backend count Unicode code points. */
export function sentenceAt(text: string, targetStart: number, targetEnd: number, language: "ja" | "en" = "ja"): string {
  const characters = Array.from(text);
  let offset = 0;
  const segmenter = new Intl.Segmenter(language, { granularity: "sentence" });
  for (const part of segmenter.segment(text)) {
    const length = Array.from(part.segment).length;
    if (targetStart >= offset && targetEnd <= offset + length) return part.segment.trim();
    offset += length;
  }
  return characters.slice(0).join("").trim();
}

/** Find the edited sentence in the transcript, containing this exact occurrence. */
export function sentenceOffsets(text: string, sentence: string, targetStart: number, targetEnd: number): { start: number; end: number } | null {
  const source = Array.from(text);
  const selection = Array.from(sentence.trim());
  if (!selection.length) return null;
  for (let start = Math.max(0, targetEnd - selection.length); start <= targetStart; start++) {
    const end = start + selection.length;
    if (end >= targetEnd && source.slice(start, end).join("") === selection.join("")) return { start, end };
  }
  return null;
}
