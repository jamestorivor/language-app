import { useLanguage } from "../i18n-context";
import { useEffect, useState } from "react";
import { getStudySettings, saveStudySettings } from "../api/study";
import { defaultStudyShortcuts, shortcutLabel, shortcutOptions } from "../utils/studyShortcuts";
import type { StudyShortcuts } from "../utils/studyShortcuts";

export default function StudySettings() {
  const { t } = useLanguage();
  const [retention, setRetention] = useState("90");
  const [maximum, setMaximum] = useState("36500");
  const [fuzzing, setFuzzing] = useState(true);
  const [shortcuts, setShortcuts] = useState<StudyShortcuts>(defaultStudyShortcuts);
  const [loading, setLoading] = useState(true);
  const [loaded, setLoaded] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    void getStudySettings().then((settings) => {
      if (!active) return;
      setRetention(String(settings.retention_percent));
      setMaximum(String(settings.maximum_interval));
      setFuzzing(settings.fuzzing);
      setShortcuts(settings.shortcuts);
      setLoaded(true);
    }).catch(() => {
      if (active) setError("Could not load study settings. Please try again.");
    }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [attempt]);

  async function save(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (saving) return;
    const retentionPercent = Number(retention);
    const maximumInterval = Number(maximum);
    if (!retention || !Number.isInteger(retentionPercent) || retentionPercent < 70 || retentionPercent > 97 ||
        !maximum || !Number.isInteger(maximumInterval) || maximumInterval < 1 || maximumInterval > 36500) {
      setError("Enter a retention from 70 to 97% and a maximum interval from 1 to 36,500 days.");
      return;
    }
    if (new Set(Object.values(shortcuts)).size !== 5) {
      setError("Choose a different key for each review action.");
      return;
    }
    setSaving(true);
    setError("");
    setNotice("");
    try {
      const saved = await saveStudySettings({ retention_percent: retentionPercent, maximum_interval: maximumInterval, fuzzing, shortcuts });
      setRetention(String(saved.retention_percent));
      setMaximum(String(saved.maximum_interval));
      setFuzzing(saved.fuzzing);
      setShortcuts(saved.shortcuts);
      setNotice("Study settings saved.");
    } catch {
      setError("Could not save study settings. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="text-lg font-semibold text-stone-900">{t("Study settings")}</h1>
      {loading && <p role="status" className="mt-6 text-stone-500">{t("Loading settings…")}</p>}
      {error && <p role="alert" className="mt-6 text-sm text-red-700">{t(error)} {!loaded && !loading && <button type="button" onClick={() => setAttempt((value) => value + 1)} className="font-semibold underline">{t("Try again")}</button>}</p>}
      {notice && <p role="status" className="mt-6 text-sm text-emerald-800">{t(notice)}</p>}
      {loaded && <form onSubmit={(event) => void save(event)} className="mt-6 space-y-6 rounded-2xl border border-stone-200 bg-white p-6 shadow-sm sm:p-8">
        <div>
          <label htmlFor="retention" className="block text-sm font-semibold text-stone-900">{t("Desired retention (%)")}</label>
          <p id="retention-help" className="mt-1 text-sm text-stone-600">{t("Your target chance of remembering a card at review time. A higher target usually means more reviews.")}</p>
          <input id="retention" type="number" min="70" max="97" step="1" required value={retention} onChange={(event) => { setRetention(event.target.value); setNotice(""); }} aria-describedby="retention-help" className="mt-3 w-32 rounded-lg border border-stone-300 px-3 py-2" />
          <p className="mt-1 text-xs text-stone-500">{t("70–97%; default 90%")}</p>
        </div>
        <div>
          <label htmlFor="maximum" className="block text-sm font-semibold text-stone-900">{t("Maximum review interval (days)")}</label>
          <p id="maximum-help" className="mt-1 text-sm text-stone-600">{t("The longest interval FSRS can schedule between reviews.")}</p>
          <input id="maximum" type="number" min="1" max="36500" step="1" required value={maximum} onChange={(event) => { setMaximum(event.target.value); setNotice(""); }} aria-describedby="maximum-help" className="mt-3 w-32 rounded-lg border border-stone-300 px-3 py-2" />
          <p className="mt-1 text-xs text-stone-500">{t("1–36,500 days; default 36,500")}</p>
        </div>
        <div>
          <label className="flex items-start gap-3 text-sm font-semibold text-stone-900"><input type="checkbox" checked={fuzzing} onChange={(event) => { setFuzzing(event.target.checked); setNotice(""); }} className="mt-1" /> {t("Spread reviews across days")}</label>
          <p className="mt-1 pl-6 text-sm text-stone-600">{t("Adds a small amount of variation to longer intervals to avoid reviews piling up on the same day.")}</p>
        </div>
        <p className="rounded-xl bg-stone-50 p-4 text-sm leading-6 text-stone-600">{t("Changes apply when each card is next reviewed; existing due dates stay as they are. For familiar words at levels 3 and 4, reviews are instead eligible when predicted recall reaches 80%, which may be later than the maximum FSRS interval. Learning steps keep their usual timing.")}</p>
        <fieldset className="border-t border-stone-200 pt-6" disabled={saving}>
          <legend className="text-lg font-semibold text-stone-900">{t("Keyboard shortcuts")}</legend>
          <p className="mt-2 text-sm text-stone-600">{t("Choose a different key for each review action.")}</p>
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            {([ ["show_answer", "Show answer"], ["again", "Again"], ["hard", "Hard"], ["good", "Good"], ["easy", "Easy"] ] as const).map(([action, label]) =>
              <label key={action} className="block text-sm font-semibold text-stone-700">{t(label)}
                <select value={shortcuts[action]} onChange={(event) => { setShortcuts({ ...shortcuts, [action]: event.target.value }); setNotice(""); setError(""); }} className="mt-2 block w-full rounded-lg border border-stone-300 bg-white px-3 py-2 font-normal focus:outline-2 focus:outline-emerald-800">
                  {shortcutOptions.map((key) => <option key={key} value={key}>{t(shortcutLabel(key))}</option>)}
                </select>
              </label>)}
          </div>
          <button type="button" onClick={() => { setShortcuts(defaultStudyShortcuts); setError(""); setNotice(""); }} className="mt-4 text-sm font-semibold text-emerald-800 underline">{t("Reset shortcuts")}</button>
        </fieldset>
        <button type="submit" disabled={saving} className="rounded-xl bg-emerald-900 px-5 py-3 text-sm font-semibold text-white hover:bg-emerald-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-800 disabled:opacity-50">{saving ? t("Saving…") : t("Save settings")}</button>
      </form>}
    </div>
  );
}
