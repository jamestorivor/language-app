import { useEffect, useState } from "react";
import { useLanguage } from "../i18n-context";
import { API_BASE_URL } from "../api/config";
import { loggedFetch } from "../api/client";

type Language = "ja" | "en";
type LevelProgress = { level: string; known: number; total: number };
const levels: Record<Language, string[]> = {
  ja: ["N5", "N4", "N3", "N2", "N1"],
  en: ["A1", "A2", "B1", "B2", "C1", "C2"],
};

async function loadProgress(language: Language): Promise<LevelProgress[]> {
  const url = new URL("vocabulary/mark-known", API_BASE_URL);
  url.searchParams.set("language", language);
  const response = await loggedFetch("get_mark_known_progress", url);
  if (!response.ok) throw new Error("Request failed");
  return response.json();
}

export default function MarkKnown() {
  const { t, locale } = useLanguage();
  const [language, setLanguage] = useState<Language>(() => locale === "ja" ? "en" : "ja");
  const [level, setLevel] = useState(() => locale === "ja" ? "A1" : "N5");
  const [progress, setProgress] = useState<LevelProgress[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    setLoading(true);
    setLoadError(false);
    setProgress(null);
    loadProgress(language).then((data) => {
      if (active) setProgress(data);
    }).catch(() => {
      if (active) setLoadError(true);
    }).finally(() => {
      if (active) setLoading(false);
    });
    return () => { active = false; };
  }, [language]);

  // A level is complete only if every easier level also has data and is complete.
  const completed = progress?.reduce<string | null>((current, item, index) => {
    if ((index === 0 || current === progress[index - 1].level) && item.total > 0 && item.known === item.total) return item.level;
    return current;
  }, null);
  const included = levels[language].slice(0, levels[language].indexOf(level) + 1).join(", ");

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setMessage("");
    setError("");
    try {
      const response = await loggedFetch("mark_known_by_level", new URL("vocabulary/mark-known", API_BASE_URL), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ language, level }),
      });
      if (!response.ok) throw new Error("Request failed");
      const result: { matched_words: number } = await response.json();
      setMessage(result.matched_words === 0
        ? t("No matching words were found. Make sure the dictionary and level data have been imported.")
        : t("Marked {count} words as known.", { count: result.matched_words.toLocaleString(locale) }));
      try {
        setProgress(await loadProgress(language));
        setLoadError(false);
      } catch {
        setProgress(null);
        setLoadError(true);
      }
    } catch {
      setError(t("Could not update your words. Please try again."));
    } finally {
      setPending(false);
    }
  }

  return (
    <section className="mt-6 max-w-3xl rounded-3xl border border-stone-200 bg-white px-6 py-8 shadow-sm sm:px-12">
      <h2 className="text-xl font-bold tracking-tight text-stone-950">{t("Mark words you already know")}</h2>
      <p className="mt-2 text-sm leading-6 text-stone-600">{t("Start with a level to mark its words and all easier words as known.")}</p>
      <label className="mt-6 flex flex-col items-start gap-1.5 text-sm font-medium text-stone-700">
        {t("Language")}
        <select value={language} disabled={pending} onChange={(event) => {
          const next = event.target.value as Language;
          setLanguage(next);
          setLevel(levels[next][0]);
          setMessage("");
          setError("");
        }} className="rounded-lg border border-stone-300 bg-white px-3 py-2 text-stone-900">
          <option value="ja">日本語</option>
          <option value="en">English</option>
        </select>
      </label>

      <div className="mt-5 rounded-2xl bg-stone-50 p-5" aria-live="polite">
        <h3 className="text-sm font-semibold text-stone-900">{t("Your current marked level")}</h3>
        {loading ? <p className="mt-2 text-sm text-stone-600">{t("Loading your progress…")}</p>
          : loadError ? <p className="mt-2 text-sm text-red-700">{t("Could not load your current progress. Please refresh the page to try again.")}</p>
          : <>
            <p className="mt-2 text-lg font-bold text-emerald-900">{completed ? t("Fully marked through {level}", { level: completed }) : t("No level fully marked yet")}</p>
            <p className="mt-1 text-sm leading-6 text-stone-600">{t("A level is fully marked when all listed words at that level and easier levels have a rating of 5.")}</p>
            <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-3">
              {progress?.map((item) => <div key={item.level} className="rounded-xl border border-stone-200 bg-white px-3 py-2">
                <p className="text-sm font-semibold text-stone-900">{item.level}</p>
                <p className="mt-0.5 text-xs text-stone-600">{item.total === 0 ? t("No level data") : t("{known} / {total} known", { known: item.known.toLocaleString(locale), total: item.total.toLocaleString(locale) })}</p>
              </div>)}
            </div>
          </>}
      </div>

      <form onSubmit={submit} className="mt-6">
        <h3 className="text-sm font-semibold text-stone-900">{t("Choose a level to mark")}</h3>
        <label className="mt-3 flex flex-col items-start gap-1.5 text-sm font-medium text-stone-700">
          {language === "ja" ? t("JLPT level") : t("CEFR level")}
          <select value={level} disabled={pending} onChange={(event) => { setLevel(event.target.value); setMessage(""); setError(""); }} className="rounded-lg border border-stone-300 bg-white px-3 py-2 text-stone-900">
            {levels[language].map((item) => <option key={item} value={item}>{item}</option>)}
          </select>
        </label>
        <p className="mt-3 text-sm leading-6 text-stone-700">{t("This will mark words in: {levels}.", { levels: included })}</p>
        <p className="mt-1 text-sm leading-6 text-stone-600">{t("These words will be rated 5, replacing any existing ratings. Choosing a lower level will not undo previous ratings. Level lists are approximate and do not cover every word.")}</p>
        <button disabled={pending || loading} className="mt-4 rounded-lg bg-emerald-900 px-4 py-2.5 text-sm font-semibold text-white hover:bg-emerald-800 disabled:opacity-50">
          {pending ? t("Updating…") : t("Mark as known")}
        </button>
      </form>
      {message && <p role="status" className="mt-4 text-sm text-emerald-800">{message}</p>}
      {error && <p role="alert" className="mt-4 text-sm text-red-700">{error}</p>}
    </section>
  );
}
