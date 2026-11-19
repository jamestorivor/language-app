import { useLanguage } from "../i18n-context";
import { useEffect, useState } from "react";
import { Link } from "react-router";
import { getStudySources } from "../api/study";
import type { StudyCard, StudySource } from "../api/study";
import { formatTime } from "../utils/formatTime";

/** Offsets refer to Unicode code points, as they do in the Python backend. */
export function HighlightedSentence({ text, target, start, end }: {
  text: string; target: string; start: number | null | undefined; end: number | null | undefined;
}) {
  const characters = Array.from(text);
  if (start == null || end == null || !Number.isInteger(start) || !Number.isInteger(end) || start < 0 || end <= start || end > characters.length || characters.slice(start, end).join("") !== target) {
    return <>{text}</>;
  }
  return <>{characters.slice(0, start).join("")}<mark className="rounded bg-amber-200 px-0.5 text-stone-950">{characters.slice(start, end).join("")}</mark>{characters.slice(end).join("")}</>;
}

function timeLabel(source: StudySource) {
  return source.start_ms !== null && source.timing === "cue" ? formatTime(source.start_ms / 1000) : "Timestamp unavailable";
}

export default function StudyContext({ card, compact = false }: { card: StudyCard; compact?: boolean }) {
  const { t } = useLanguage();
  const [sources, setSources] = useState<StudySource[] | null>(null);
  const [selected, setSelected] = useState<number | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let active = true;
    void getStudySources(card.id).then((result) => {
      if (!active) return;
      setSources(result);
      setSelected((result.find((item) => item.card_id === card.id) ?? result[0])?.id ?? null);
    }).catch(() => { if (active) setError(true); });
    return () => { active = false; };
  }, [card.id]);

  const source = sources?.find((item) => item.id === selected);
  const fallbackStart = card.target_start === undefined ? null : card.target_start - card.sentence_start;
  const fallbackEnd = card.target_end === undefined ? null : card.target_end - card.sentence_start;
  const segmentLink = source?.segment_id != null
    ? `/podcasts/segments/${source.segment_id}?study_card=${source.card_id}&context=${source.id}` : null;
  const sourceDetails = <>
    {sources && sources.length > 1 && <label className="block text-sm font-semibold text-stone-700">{t("Source sentence")}
      <select aria-label={t("Source sentence")} value={selected ?? ""} onChange={(event) => setSelected(Number(event.target.value))} className="mt-2 block w-full rounded-lg border border-stone-300 bg-white px-3 py-2 font-normal text-stone-800">
        {sources.map((item) => <option key={item.id} value={item.id}>{item.episode_title || t("Episode unavailable")} · {t(timeLabel(item))} · {item.sentence.slice(0, 36)}</option>)}
      </select>
    </label>}
    {source && <>
      {source.dictionary_form && source.dictionary_form !== source.target_text && <p className="mt-2 text-sm text-stone-600">{t("Dictionary form:")} <span lang={card.language ?? "ja"}>{source.dictionary_form}</span> {t("· In sentence:")} <span lang={card.language ?? "ja"}>{source.target_text}</span></p>}
      <p className="mt-3 text-sm text-stone-600">{source.episode_title || t("Episode unavailable")} · {t(timeLabel(source))}</p>
      {source.timing === "cue" && source.start_ms !== null && <p className="mt-1 text-xs text-stone-500">{t("Time is from the source caption, which may cover more than one sentence.")}</p>}
      {source.source_status === "changed" && <p className="mt-2 text-sm text-amber-800">{t("The transcript has changed; the saved sentence is shown here and may no longer match the current transcript.")}</p>}
      {source.source_status === "missing" && <p className="mt-2 text-sm text-stone-600">{t("The original segment or episode is no longer available.")}</p>}
      {segmentLink ? <Link to={segmentLink} className="mt-3 inline-block rounded-lg border border-emerald-800 px-3 py-2 text-sm font-semibold text-emerald-900 hover:bg-emerald-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-800">{source.source_status !== "available" ? t("Open source segment") : source.start_ms !== null ? t("Listen in context") : t("Go to sentence")}</Link>
        : source.episode_id !== null ? <Link to={`/podcasts/${source.episode_id}`} className="mt-3 inline-block rounded-lg border border-emerald-800 px-3 py-2 text-sm font-semibold text-emerald-900 hover:bg-emerald-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-800">{t("Open source episode")}</Link> : null}
    </>}
    {!source && (error || sources !== null) && <>
      <p className="mt-3 text-sm text-stone-600">{card.episode_title || t("Episode unavailable")} · {t("Timestamp unavailable")}</p>
      {card.episode_id != null && <Link to={`/podcasts/${card.episode_id}`} className="mt-3 inline-block rounded-lg border border-emerald-800 px-3 py-2 text-sm font-semibold text-emerald-900 hover:bg-emerald-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-800">{t("Open source episode")}</Link>}
    </>}
  </>;
  return <section aria-label={t("Source sentence")} className={`mt-5 ${compact ? "review-source" : ""}`}>
    {!sources && !error && <p className="text-sm text-stone-500" role="status">{t("Loading source context…")}</p>}
    {error && <p className="text-sm text-red-700" role="alert">{t("Could not load the original source. The saved sentence is shown below.")}</p>}
    {source && source.card_id === card.id && source.sentence !== card.sentence && <div className="mt-4">
      <h3 className="text-xs font-bold uppercase tracking-[0.12em] text-stone-500">{t("Study sentence")}</h3>
      <p className="mt-2 whitespace-pre-wrap break-words text-lg leading-relaxed text-stone-900" lang={card.language ?? "ja"}>{card.sentence}</p>
    </div>}
    <h3 className="mt-4 text-xs font-bold uppercase tracking-[0.12em] text-stone-500">{t("Original sentence")}</h3>
    <p className="mt-2 whitespace-pre-wrap break-words text-lg leading-relaxed text-stone-900" lang={card.language ?? "ja"}>
      {source ? <HighlightedSentence text={source.sentence} target={source.target_text} start={source.target_start} end={source.target_end} />
        : <HighlightedSentence text={card.sentence} target={card.target_text} start={fallbackStart} end={fallbackEnd} />}
    </p>
    {card.sentence_translation && (!source || source.card_id === card.id) && <p className="mt-2 text-stone-600">{card.sentence_translation}</p>}
    {compact ? <details className="review-source-details"><summary>{t("Source details")}</summary>{sourceDetails}</details> : sourceDetails}
  </section>;
}
