import { useLanguage } from "../i18n-context";
import type { StudyLanguage } from "../utils/studyLanguage";

export function StudyLanguageSelector({ language, onChange, disabled }: { language: StudyLanguage; onChange: (value: StudyLanguage) => void; disabled?: boolean }) {
  const { t } = useLanguage();
  return <fieldset disabled={disabled} aria-label={t("Study language")} className="mt-6 inline-flex rounded-xl bg-stone-200/70 p-1">
    {([ ["ja", "日本語"], ["en", "English"] ] as const).map(([value, label]) =>
      <button key={value} type="button" aria-pressed={language === value} onClick={() => onChange(value)}
        className={`rounded-lg px-4 py-2 text-sm font-semibold transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-800 disabled:opacity-50 ${language === value ? "bg-white text-emerald-900 shadow-sm" : "text-stone-600 hover:text-stone-900"}`}>
        {label}
      </button>)}
  </fieldset>;
}
