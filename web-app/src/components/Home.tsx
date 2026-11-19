import { Link } from "react-router";
import { useLanguage } from "../i18n-context";
import { useStudyLanguage } from "../utils/studyLanguage";
import KnownWordCount from "./KnownWordCount";

export default function Home() {
  const { t } = useLanguage();
  const [language] = useStudyLanguage();
  const reviewLabel = t("Start {language} review", { language: language === "ja" ? "日本語" : "English" });

  return (
    <>
      <p className="text-xs font-bold uppercase tracking-[0.16em] text-emerald-800">{t("Your learning")}</p>
      <h1 className="mt-3 text-3xl font-bold tracking-tight text-stone-950 sm:text-4xl">{t("Welcome back")}</h1>
      <p className="mt-3 text-base text-stone-600">{t("Pick up where you left off.")}</p>

      <section className="mt-8 rounded-3xl bg-emerald-900 px-6 py-7 text-white sm:px-8 sm:py-8" aria-labelledby="review-heading">
        <h2 id="review-heading" className="text-xl font-bold">{t("Ready to review?")}</h2>
        <p className="mt-2 text-sm leading-6 text-emerald-100">{t("Practice your due cards.")}</p>
        <KnownWordCount language={language} light />
        <div>
          <Link to="/study/review" className="mt-5 inline-flex items-center gap-3 rounded-xl bg-white px-5 py-3 text-sm font-semibold text-emerald-900 transition-colors hover:bg-emerald-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white">
            {reviewLabel}<span aria-hidden="true">→</span>
          </Link>
        </div>
      </section>

      <div className="mt-5 grid gap-4 sm:grid-cols-2">
        <Link to="/podcasts" aria-label={t("My podcasts")} className="group rounded-2xl border border-stone-200 bg-white p-6 shadow-sm transition-colors hover:border-emerald-300 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-800">
          <span className="flex items-center justify-between gap-4 text-lg font-semibold text-stone-950">
            <span className="flex items-center gap-3"><svg aria-hidden="true" viewBox="0 0 24 24" className="h-5 w-5 shrink-0 text-emerald-800" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M3 14v-2a9 9 0 0 1 18 0v2" /><path d="M3 14a2 2 0 0 1 2-2h1v7H5a2 2 0 0 1-2-2v-3ZM21 14a2 2 0 0 0-2-2h-1v7h1a2 2 0 0 0 2-2v-3Z" /></svg>{t("My podcasts")}</span>
            <span aria-hidden="true" className="text-emerald-800 transition-transform group-hover:translate-x-1">→</span>
          </span>
          <span className="mt-2 block text-sm leading-6 text-stone-600">{t("Choose an episode to continue listening.")}</span>
        </Link>
        <Link to="/study" aria-label={t("Study")} className="group rounded-2xl border border-stone-200 bg-white p-6 shadow-sm transition-colors hover:border-emerald-300 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-800">
          <span className="flex items-center justify-between gap-4 text-lg font-semibold text-stone-950">
            <span className="flex items-center gap-3"><svg aria-hidden="true" viewBox="0 0 24 24" className="h-5 w-5 shrink-0 text-emerald-800" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M12 7c-2-2-5-2.5-9-1v13c4-1.5 7-1 9 1m0-13c2-2 5-2.5 9-1v13c-4-1.5-7-1-9 1m0-13v13" /></svg>{t("Study")}</span>
            <span aria-hidden="true" className="text-emerald-800 transition-transform group-hover:translate-x-1">→</span>
          </span>
          <span className="mt-2 block text-sm leading-6 text-stone-600">{t("Browse your cards and track your progress.")}</span>
        </Link>
      </div>
    </>
  );
}
