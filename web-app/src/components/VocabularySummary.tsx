import type { VocabularyComparison, VocabularyEstimate } from "../contracts/podcast";

// Round the endpoints outward so the displayed range still includes the estimate.
function formatRange(low: number, high: number) {
  if (low === high) return String(Math.round(low));
  return `${Math.floor(low)}–${Math.ceil(high)}`;
}

function formatDate(value: string | null | undefined) {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date.toLocaleDateString(undefined, { dateStyle: "medium" });
}

function FamiliarityRing({ estimate, compact = false }: { estimate: VocabularyEstimate; compact?: boolean }) {
  const low = Math.max(0, Math.min(100, estimate.familiarity_low));
  const high = Math.max(low, Math.min(100, estimate.familiarity_high));
  return (
    <span className={`relative inline-flex shrink-0 items-center justify-center ${compact ? "h-5 w-5" : "h-32 w-32 sm:h-36 sm:w-36"}`}>
      <svg viewBox="0 0 100 100" className="h-full w-full -rotate-90" aria-hidden="true">
        <circle cx="50" cy="50" r="43" fill="none" stroke="currentColor" strokeWidth="8" className="text-stone-200" />
        {high > low && <circle cx="50" cy="50" r="43" fill="none" stroke="currentColor" strokeWidth="8" pathLength="100" strokeDasharray={`${high - low} ${100 - (high - low)}`} strokeDashoffset={-low} className="text-amber-400" />}
        {low > 0 && <circle cx="50" cy="50" r="43" fill="none" stroke="currentColor" strokeWidth="8" pathLength="100" strokeDasharray={`${low} ${100 - low}`} className="text-emerald-700" />}
      </svg>
      {!compact && <span className="absolute max-w-[70%] text-center">
        <span className="block text-lg font-bold tracking-tight tabular-nums text-stone-900 sm:text-xl">{formatRange(low, high)}</span>
        <span className="mt-0.5 block text-xs text-stone-500">out of 100</span>
      </span>}
    </span>
  );
}

function DateAdded({ value }: { value?: string | null }) {
  return <p className="text-sm text-stone-500"><span className="font-medium text-stone-600">Date added</span> · {formatDate(value) ?? "Not recorded"}</p>;
}

export default function VocabularySummary({ comparison, baselineAt, addedAt, compact = false, segmentsWithText, segmentCount }: {
  comparison: VocabularyComparison | null | undefined;
  baselineAt?: string | null;
  addedAt?: string | null;
  compact?: boolean;
  segmentsWithText?: number;
  segmentCount?: number;
}) {
  const current = comparison?.current;
  if (compact) {
    if (!current) return null;
    return <span className="mt-2 inline-flex max-w-full items-center gap-1.5 rounded-lg bg-stone-100/80 px-2 py-1 text-xs text-stone-600">
      <FamiliarityRing estimate={current} compact />
      <span>Vocabulary <strong className="font-semibold tabular-nums text-stone-800">{formatRange(current.familiarity_low, current.familiarity_high)}</strong><span className="text-stone-500"> / 100</span></span>
    </span>;
  }

  const before = comparison?.baseline;
  return (
    <section aria-label="Vocabulary estimate" className="rounded-2xl border border-stone-200 bg-white p-5 text-left shadow-sm sm:p-6">
      {current ? <div className="flex flex-wrap items-center gap-x-7 gap-y-4">
        <FamiliarityRing estimate={current} />
        <div className="min-w-[11rem] flex-1">
          <p className="text-xs font-bold uppercase tracking-[0.14em] text-emerald-800">Vocabulary</p>
          <h2 className="mt-1 text-xl font-semibold tracking-tight text-stone-900">Average familiarity</h2>
          <p className="mt-1 text-sm text-stone-500">Estimated range</p>
          <div className="mt-4"><DateAdded value={addedAt} /></div>
        </div>
      </div> : <div>
        <h2 className="text-lg font-semibold text-stone-900">Vocabulary estimate</h2>
        <p className="mt-2 text-sm text-stone-500">No estimate available for this transcript.</p>
        <div className="mt-3"><DateAdded value={addedAt} /></div>
      </div>}
      {current && <details className="mt-5 border-t border-stone-100 pt-4 text-sm text-stone-600">
        <summary className="w-fit cursor-pointer font-semibold text-emerald-800 hover:text-emerald-950">About this estimate</summary>
        <p className="mt-3 leading-relaxed">The score averages matched word occurrences. Green reflects recorded ratings; amber shows the possible contribution of unrated words, which you may already know.</p>
        <dl className="mt-4 grid grid-cols-1 gap-x-6 gap-y-3 sm:grid-cols-2">
          <div><dt className="text-stone-500">Vocabulary difficulty</dt><dd className="font-semibold tabular-nums text-stone-800">{formatRange(current.difficulty_low, current.difficulty_high)} / 100</dd></div>
          <div><dt className="text-stone-500">Difficult words <span className="text-xs">(rated 1–2)</span></dt><dd className="font-semibold tabular-nums text-stone-800">{current.low_rated_unique}</dd></div>
          <div><dt className="text-stone-500">Unrated words</dt><dd className="font-semibold tabular-nums text-stone-800">{current.unrated_unique}</dd></div>
          <div><dt className="text-stone-500">Rated occurrences</dt><dd className="font-semibold tabular-nums text-stone-800">{current.rated_percent}% of {current.matched_occurrences}</dd></div>
          <div><dt className="text-stone-500">Dictionary matches</dt><dd className="font-semibold tabular-nums text-stone-800">{current.dictionary_match_percent}% · {current.unmatched_groups} unmatched</dd></div>
          {before && <div><dt className="text-stone-500">Baseline{formatDate(baselineAt) ? ` · ${formatDate(baselineAt)}` : ""}</dt><dd className="font-semibold tabular-nums text-stone-800">{formatRange(before.familiarity_low, before.familiarity_high)} / 100</dd></div>}
        </dl>
        {before && <p className="mt-4">Since the baseline: {comparison.improved_unique} ratings increased, {comparison.declined_unique} decreased, and {comparison.newly_rated_unique} words were newly rated.</p>}
        {segmentsWithText !== undefined && segmentCount !== undefined && segmentsWithText < segmentCount && <p className="mt-2">The estimate covers {segmentsWithText} of {segmentCount} segments with transcript text.</p>}
        <p className="mt-2 leading-relaxed">Unmatched words are excluded. The estimate does not measure grammar or listening comprehension. Rating changes may reflect knowledge you already had or learned elsewhere.</p>
      </details>}
    </section>
  );
}
