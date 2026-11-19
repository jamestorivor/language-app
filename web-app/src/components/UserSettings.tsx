import { useLanguage } from "../i18n-context";
import MarkKnown from "./MarkKnown";

export default function UserSettings() {
  const { t, locale, setLocale } = useLanguage();

  return (
    <div className="max-w-3xl">
      <p className="text-xs font-bold uppercase tracking-[0.16em] text-emerald-800">{t("Your account")}</p>
      <h1 className="mt-3 text-3xl font-bold tracking-tight text-stone-950 sm:text-4xl">{t("User settings")}</h1>
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
      <MarkKnown key={locale} />
    </div>
  );
}
