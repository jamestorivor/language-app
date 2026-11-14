export type TranscriptFileFormat = "txt" | "srt" | "vtt";

export async function readTranscriptFile(value: FormDataEntryValue | null): Promise<{ text: string; format: TranscriptFileFormat } | undefined> {
  if (!(value instanceof File) || !value.name) return undefined;
  const extension = value.name.toLowerCase().split(".").pop();
  if (extension !== "txt" && extension !== "srt" && extension !== "vtt") throw new Error("Choose a .txt, .srt, or .vtt transcript file.");
  if (value.size > 1_000_000) throw new Error("The transcript file must be 1 MB or smaller.");
  try {
    return { text: new TextDecoder("utf-8", { fatal: true }).decode(await value.arrayBuffer()), format: extension };
  } catch {
    throw new Error("The transcript file must be encoded as UTF-8.");
  }
}
