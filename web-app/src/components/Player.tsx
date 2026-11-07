export default function PodcastPlayer() {
  return (
    <div className="w-full max-w-xl rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="mb-4">
        <p className="text-sm font-medium text-indigo-600">Podcast episode</p>
        <h2 className="text-lg font-semibold text-slate-900">Episode title</h2>
        <p className="text-sm text-slate-500">Podcast name</p>
      </div>

      <audio
        className="w-full"
        controls
        preload="metadata"
        src="/audio/placeholder.mp3"
      >
        Your browser does not support audio playback.
      </audio>
    </div>
  );
}
