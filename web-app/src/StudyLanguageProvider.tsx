import { useEffect, useRef, useState, type ReactNode } from "react";
import { loggedFetch } from "./api/client";
import { API_BASE_URL } from "./api/config";
import { useLanguage } from "./i18n-context";
import { StudyLanguageContext, studyLevels, type StudyLanguage } from "./utils/studyLanguage";

export function StudyLanguageProvider({ children, accountControl }: { children: ReactNode; accountControl?: ReactNode }) {
  const { t } = useLanguage();
  const [language, setLanguage] = useState<StudyLanguage | null>(null);
  const [levels, setLevels] = useState<Record<StudyLanguage, string | null>>({ ja: null, en: null });
  const [noWords, setNoWords] = useState(false);
  const [onboardingRequired, setOnboardingRequired] = useState(false);
  const [selection, setSelection] = useState<StudyLanguage | null>(null);
  const [level, setLevel] = useState("");
  const [loadError, setLoadError] = useState<"unavailable" | "configuration" | null>(null);
  const [saveError, setSaveError] = useState(false);
  const [saving, setSaving] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const savingRef = useRef(false);

  useEffect(() => {
    let active = true;
    setLoadError(null);
    void loggedFetch("profile.read", new URL("profile", API_BASE_URL)).then(async (response) => {
      if (response.status === 503) {
        if (active) setLoadError("configuration");
        return;
      }
      if (!response.ok) throw new Error("Could not load profile");
      const profile = await response.json();
      if (profile.learning_language !== "ja" && profile.learning_language !== "en") throw new Error("Invalid learning language");
      if (active) {
        setLanguage(profile.learning_language);
        setLevels({ ja: profile.levels?.ja ?? null, en: profile.levels?.en ?? null });
        setOnboardingRequired(profile.onboarding_required === true);
      }
    }).catch(() => { if (active) setLoadError("unavailable"); });
    return () => { active = false; };
  }, [attempt]);

  async function chooseLanguage(next: StudyLanguage, selectedLevel?: string) {
    if (savingRef.current) return false;
    if (next === language && !onboardingRequired) return true;
    savingRef.current = true;
    setSaving(true);
    setSaveError(false);
    try {
      const response = await loggedFetch(onboardingRequired ? "profile.onboarding" : "profile.update", new URL(onboardingRequired ? "profile/onboarding" : "profile", API_BASE_URL), {
        method: onboardingRequired ? "POST" : "PUT", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(onboardingRequired ? { learning_language: next, level: selectedLevel || null } : { learning_language: next }),
      });
      if (!response.ok) throw new Error("Could not save profile");
      if (onboardingRequired) {
        const result = await response.json();
        setLevels((previous) => ({ ...previous, [next]: selectedLevel || null }));
        setNoWords(result.matched_words === 0);
      }
      setLanguage(next);
      setOnboardingRequired(false);
      return true;
    } catch {
      if (onboardingRequired) {
        try {
          const response = await loggedFetch("profile.read", new URL("profile", API_BASE_URL));
          if (response.ok) {
            const profile = await response.json();
            if (profile.onboarding_required === false && (profile.learning_language === "ja" || profile.learning_language === "en")) {
              setLanguage(profile.learning_language);
              setLevels({ ja: profile.levels?.ja ?? null, en: profile.levels?.en ?? null });
              setOnboardingRequired(false);
              return true;
            }
          }
        } catch { /* Keep the form available if the profile cannot be checked. */ }
      }
      setSaveError(true); return false;
    }
    finally { savingRef.current = false; setSaving(false); }
  }

  async function chooseLevel(nextLanguage: StudyLanguage, nextLevel: string | null) {
    if (savingRef.current) return false;
    savingRef.current = true;
    setSaving(true);
    try {
      const response = await loggedFetch("profile.level", new URL("profile/level", API_BASE_URL), {
        method: "PUT", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ language: nextLanguage, level: nextLevel }),
      });
      if (!response.ok) throw new Error("Could not save level");
      setLevels((previous) => ({ ...previous, [nextLanguage]: nextLevel }));
      return true;
    } catch { return false; }
    finally { savingRef.current = false; setSaving(false); }
  }

  if (loadError) return <main className="p-8" role="alert">{t(loadError === "configuration" ? "The server is not configured for sign-in. Check the backend authentication settings and restart it." : "Could not load your learning language.")} <button className="underline" onClick={() => setAttempt((value) => value + 1)}>{t("Try again")}</button></main>;
  if (!language) return <p className="p-8" role="status">{t("Loading your profile…")}</p>;
  if (onboardingRequired) return <main className="min-h-screen bg-[#f7f7f4] px-6 py-8 text-stone-950 sm:py-12">
    <div className="mx-auto max-w-xl">
      <div className="flex items-center justify-between gap-4">
        <p className="text-xs font-bold uppercase tracking-[0.16em] text-emerald-800">{t("Get started")}</p>
        {accountControl}
      </div>
      <section className="mt-10 rounded-3xl border border-stone-200 bg-white p-6 shadow-sm sm:mt-16 sm:p-10">
        <h1 className="text-3xl font-bold tracking-tight">{t("What would you like to learn?")}</h1>
        <p className="mt-3 leading-6 text-stone-600">{t("Choose a language to get started. You can change it later in settings.")}</p>
        <form className="mt-8" onSubmit={(event) => { event.preventDefault(); if (selection) void chooseLanguage(selection, level); }}>
          <fieldset disabled={saving}>
            <legend className="text-sm font-semibold text-stone-700">{t("Your learning language")}</legend>
            <div className="mt-3 grid gap-3 sm:grid-cols-2">
              {([["ja", "日本語", "Japanese"], ["en", "English", "English"]] as const).map(([value, native, label]) => <label key={value} className={`flex cursor-pointer items-center gap-3 rounded-2xl border p-4 transition ${selection === value ? "border-emerald-800 bg-emerald-50" : "border-stone-200 hover:border-emerald-400"}`}>
                <input className="accent-emerald-800" type="radio" name="learning-language" value={value} checked={selection === value} onChange={() => { setSelection(value); setLevel(""); setSaveError(false); }} />
                <span><span className="block font-semibold">{native}</span>{native !== label && <span className="text-sm text-stone-500">{t(label)}</span>}</span>
              </label>)}
            </div>
          </fieldset>
          {selection && <div className="mt-7 border-t border-stone-200 pt-6">
            <label className="block text-sm font-semibold text-stone-700" htmlFor="starting-level">{t("Words you already know (optional)")}</label>
            <p className="mt-2 text-sm leading-6 text-stone-600">{t("Choose a level to mark its words and all easier words as known. You can also do this later in settings.")}</p>
            <select id="starting-level" value={level} disabled={saving} onChange={(event) => { setLevel(event.target.value); setSaveError(false); }} className="mt-3 w-full rounded-lg border border-stone-300 bg-white px-3 py-2.5 text-stone-900">
              <option value="">{t("Start without marking words")}</option>
              {studyLevels[selection].map((item) => <option key={item} value={item}>{selection === "ja" ? "JLPT" : "CEFR"} {item}</option>)}
            </select>
            {level && <p className="mt-3 text-sm leading-6 text-stone-600">{t("This will mark words in: {levels}.", { levels: studyLevels[selection].slice(0, studyLevels[selection].indexOf(level) + 1).join(", ") })} {t("These words will be rated 5, replacing any existing ratings. Level lists are approximate and do not cover every word.")}</p>}
          </div>}
          {saveError && <p role="alert" className="mt-4 text-sm text-red-700">{t("Could not complete setup. Please try again.")}</p>}
          <button type="submit" disabled={!selection || saving} className="mt-6 w-full rounded-xl bg-emerald-900 px-5 py-3 font-semibold text-white hover:bg-emerald-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-800 disabled:cursor-not-allowed disabled:opacity-50">{saving ? t("Saving…") : t("Continue")}</button>
        </form>
      </section>
    </div>
  </main>;
  return <StudyLanguageContext.Provider value={{ language, levels, chooseLanguage, chooseLevel, saving, error: saveError }}>
    {noWords && <div role="alert" className="bg-amber-50 px-6 py-4 text-sm text-amber-900">{t("Your level was saved, but no matching words were found. Check that the dictionary and level data have been imported.")} <button className="underline" onClick={() => setNoWords(false)}>{t("Dismiss")}</button></div>}
    {children}
  </StudyLanguageContext.Provider>;
}
