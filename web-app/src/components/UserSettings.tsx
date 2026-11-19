import { useLanguage } from "../i18n-context";
import { useContext, useState } from "react";
import { useNavigate } from "react-router";
import { StudyLanguageContext, useStudyLanguage, type StudyLanguage } from "../utils/studyLanguage";
import MarkKnown from "./MarkKnown";

export default function UserSettings() {
  const { t, locale, setLocale } = useLanguage();
  const [learningLanguage, setLearningLanguage] = useStudyLanguage();
  const profile = useContext(StudyLanguageContext);
  const navigate = useNavigate();
  const [pendingLanguage, setPendingLanguage] = useState<StudyLanguage>(learningLanguage);
  const [saveFailed, setSaveFailed] = useState(false);

  async function confirmChange() {
    if (pendingLanguage === learningLanguage) return;
    setSaveFailed(false);
    if (await setLearningLanguage(pendingLanguage)) {
      navigate("/", { replace: true });
    } else setSaveFailed(true);
  }

  return (
    <div className="max-w-3xl">
      <p className="text-xs font-bold uppercase tracking-[0.16em] text-emerald-800">{t("Your account")}</p>
      <h1 className="mt-3 text-3xl font-bold tracking-tight text-stone-950 sm:text-4xl">{t("User settings")}</h1>
      <section className="mt-8 rounded-3xl border border-stone-200 bg-white px-6 py-8 shadow-sm sm:px-12">
        <h2 className="text-xl font-bold tracking-tight text-stone-950">{t("Learning language")}</h2>
        <fieldset disabled={profile?.saving} className="mt-4">
          <legend className="text-sm font-medium text-stone-700">{t("Choose the language you are learning")}</legend>
          <div className="mt-2 inline-flex rounded-xl bg-stone-200/70 p-1">
            {([["ja", "日本語"], ["en", "English"]] as const).map(([value, label]) => <button key={value} type="button" aria-pressed={pendingLanguage === value} onClick={() => { setPendingLanguage(value); setSaveFailed(false); }} className={`rounded-lg px-4 py-2 text-sm font-semibold transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-800 disabled:opacity-50 ${pendingLanguage === value ? "bg-white text-emerald-900 shadow-sm" : "text-stone-600 hover:text-stone-900"}`}>{label}</button>)}
          </div>
        </fieldset>
        <button type="button" onClick={() => void confirmChange()} disabled={profile?.saving || pendingLanguage === learningLanguage} className="mt-4 block rounded-lg bg-emerald-900 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-800 disabled:cursor-not-allowed disabled:opacity-50">{profile?.saving ? t("Saving…") : t("Confirm language change")}</button>
        {saveFailed && <p role="alert" className="mt-3 text-sm text-red-700">{t("Could not save your learning language. Please try again.")}</p>}
        <p className="mt-2 text-sm text-stone-500">{t("Your podcasts, vocabulary and study progress follow this choice. Your progress in each language is kept.")}</p>
      </section>
      <section className="mt-8 rounded-3xl border border-stone-200 bg-white px-6 py-8 shadow-sm sm:px-12">
        <h2 className="text-xl font-bold tracking-tight text-stone-950">{t("Interface language")}</h2>
        <label className="mt-4 flex flex-col items-start gap-1.5 text-sm font-medium text-stone-700">
          {t("Choose your interface language")}
          <select value={locale} onChange={(event) => setLocale(event.target.value === "ja" ? "ja" : "en")} className="rounded-lg border border-stone-300 bg-white px-3 py-2 text-stone-900 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-800">
            <option value="en">English</option>
            <option value="ja">日本語</option>
          </select>
        </label>
      </section>
      <MarkKnown key={learningLanguage} />

    </div>
  );
}
