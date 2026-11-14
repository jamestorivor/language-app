export default function TranscriptFileInput({ id }: { id: string }) {
  return (
    <div>
      <label htmlFor={id} className="block text-sm font-medium text-stone-700">
        Transcript text file <span className="font-normal text-stone-400">(optional)</span>
      </label>
      <input id={id} name="transcript" type="file" accept=".txt,text/plain" aria-describedby={`${id}-help`}
        className="mt-2 block w-full text-sm text-stone-700 file:mr-3 file:rounded-lg file:border-0 file:bg-stone-100 file:px-3 file:py-2 file:font-semibold file:text-stone-700 hover:file:bg-stone-200" />
      <p id={`${id}-help`} className="mt-2 text-sm text-stone-500">
        Upload a UTF-8 .txt file (up to 1 MB). Plain text appears in the first segment. To place text in matching segments, start every line with a timestamp, for example [01:20] Spoken words.
        {id === "edit-transcript" && " Uploading a file replaces the existing transcript."}
      </p>
    </div>
  );
}
