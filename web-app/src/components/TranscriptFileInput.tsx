export default function TranscriptFileInput({ id }: { id: string }) {
  return (
    <div>
      <label htmlFor={id} className="block text-sm font-medium text-stone-700">
        Transcript file <span className="font-normal text-stone-400">(optional)</span>
      </label>
      <input id={id} name="transcript" type="file" accept=".txt,.srt,.vtt,text/plain,text/vtt,application/x-subrip" aria-describedby={`${id}-help`}
        className="mt-2 block w-full text-sm text-stone-700 file:mr-3 file:rounded-lg file:border-0 file:bg-stone-100 file:px-3 file:py-2 file:font-semibold file:text-stone-700 hover:file:bg-stone-200" />
      <p id={`${id}-help`} className="mt-2 text-sm text-stone-500">
        Upload a UTF-8 .txt, .srt, or .vtt file (up to 1 MB). Subtitle cues are placed by their start time. Plain text appears in the first segment; to place text in matching segments, start each line with a timestamp, for example [01:20] Spoken words.
        {id === "edit-transcript" && " Uploading a file replaces the existing transcript."}
      </p>
    </div>
  );
}
