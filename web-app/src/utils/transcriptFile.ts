export async function readTranscriptFile(value: FormDataEntryValue | null): Promise<string | undefined> {
  if (!(value instanceof File) || !value.name) return undefined;
  if (!value.name.toLowerCase().endsWith(".txt")) throw new Error("Choose a .txt transcript file.");
  if (value.size > 1_000_000) throw new Error("The transcript file must be 1 MB or smaller.");
  try {
    return new TextDecoder("utf-8", { fatal: true }).decode(await value.arrayBuffer());
  } catch {
    throw new Error("The transcript file must be encoded as UTF-8.");
  }
}
