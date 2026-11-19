import { Link } from "react-router";
import { useEffect, useState } from "react";
import { useLanguage } from "../i18n-context";
import { getStudyStats } from "../api/study";
import type { StudyStats } from "../api/study";
import { useStudyLanguage } from "../utils/studyLanguage";

export default function StudyHome() {
  const { t } = useLanguage();
  const [language] = useStudyLanguage();
  const [summary, setSummary] = useState<{ language: string; stats: StudyStats | null } | null>(null);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let active = true;
    const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
    void getStudyStats(timezone, language).then((stats) => {
      if (active) setSummary({ language, stats });
    }).catch(() => {
      if (active) setSummary({ language, stats: null });
    });
    return () => { active = false; };
  }, [language, attempt]);
  const stats = summary?.language === language ? summary.stats : null;
  const reviewLabel = t("Start {language} review", { language: language === "ja" ? "日本語" : "English" });

  return <>
    <div className="flex items-start justify-between gap-4">
      <div>
        <p className="text-xs font-bold uppercase tracking-[0.16em] text-emerald-800">{t("YOUR PRACTICE")}</p>
        <h1 className="mt-3 text-3xl font-bold tracking-tight text-stone-950 sm:text-4xl">{t("Study")}</h1>
        <p className="mt-3 text-base text-stone-600">{t("Choose how you’d like to study.")}</p>
      </div>
      <Link to="/study/settings" aria-label={t("Study settings")} title={t("Study settings")} className="inline-flex h-10 w-10 items-center justify-center rounded-lg text-stone-600 hover:bg-stone-200 hover:text-stone-900 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-800">
        <svg aria-hidden="true" className="h-5 w-5" viewBox="0 0 24 24" fill="currentColor">
          <path fillRule="evenodd" d="M9.5 2h5l.7 3a7.9 7.9 0 0 1 1.7 1l3-1 2.5 4.3-2.3 2a8.6 8.6 0 0 1 0 1.4l2.3 2-2.5 4.3-3-1a7.9 7.9 0 0 1-1.7 1l-.7 3h-5l-.7-3a7.9 7.9 0 0 1-1.7-1l-3 1-2.5-4.3 2.3-2a8.6 8.6 0 0 1 0-1.4l-2.3-2L4.1 5l3 1a7.9 7.9 0 0 1 1.7-1l.7-3ZM12 8.5a3.5 3.5 0 1 0 0 7 3.5 3.5 0 0 0 0-7Z" clipRule="evenodd" />
        </svg>
      </Link>
    </div>
    <div className="mx-auto max-w-3xl">

    <nav aria-label={t("Study navigation")} className="mt-8 grid gap-3 sm:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
      <Link to="/study/review" aria-label={reviewLabel} className="flex min-h-24 items-center justify-between gap-4 rounded-xl bg-emerald-900 px-5 py-5 text-white transition-colors hover:bg-emerald-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-800 sm:px-6">
        <span><span className="block text-lg font-semibold">{reviewLabel}</span><span className="mt-1 block text-sm text-emerald-100">{t("Practice your due cards.")}</span></span>
        <span aria-hidden="true" className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-white/15 text-xl">→</span>
      </Link>
      <Link to="/study/list" className="flex min-h-20 items-center gap-3 rounded-xl border border-stone-200 bg-white px-5 py-5 text-sm font-semibold text-stone-800 hover:bg-stone-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-800">
        <svg aria-hidden="true" viewBox="0 0 24 24" className="h-5 w-5 shrink-0 text-stone-500" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M9 6h11M9 12h11M9 18h11"/><path d="M4 6h.01M4 12h.01M4 18h.01" strokeWidth="3"/></svg>
        {t("Study List")}
      </Link>
    </nav>

    <section className="mt-10" aria-labelledby="progress-heading">
      <div className="flex items-baseline justify-between gap-4">
        <h2 id="progress-heading" className="text-lg font-bold tracking-tight text-stone-950">{t("Today’s progress")}</h2>
        <span className="text-xs font-semibold text-stone-500">{language === "ja" ? "日本語" : "English"}</span>
      </div>
      <dl className="mt-4 grid gap-3 sm:grid-cols-2">
        <div className="relative overflow-hidden rounded-2xl bg-emerald-100/70 p-5 sm:row-span-2 sm:p-6">
          <dt className="text-sm font-semibold text-emerald-900">
            <span aria-hidden="true" className="mb-5 flex h-9 w-9 items-center justify-center rounded-full bg-emerald-900 text-white">
              <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m5 12 4 4L19 6" /></svg>
            </span>
            {t("Completed today")}
          </dt>
          <dd className="mt-1"><span className="block text-4xl font-bold tracking-tight tabular-nums text-emerald-950 sm:text-5xl">{stats?.completed_count ?? "—"}</span><span className="mt-3 block text-sm leading-6 text-emerald-800">{t("Cards reviewed today")}</span></dd>
        </div>
        <div className="grid grid-cols-[1fr_auto] items-center gap-4 rounded-2xl border border-stone-200 bg-white px-5 py-4">
          <dt className="text-sm font-semibold text-stone-900">{t("Due now")}<span className="mt-1 block text-xs font-normal leading-5 text-stone-500">{t("Ready to review")}</span></dt>
          <dd className="text-3xl font-bold tabular-nums text-stone-900">{stats?.due_count ?? "—"}</dd>
        </div>
        <div className="grid grid-cols-[1fr_auto] items-center gap-4 rounded-2xl border border-stone-200 bg-white px-5 py-4">
          <dt className="text-sm font-semibold text-stone-900">{t("Due today")}<span className="mt-1 block text-xs font-normal leading-5 text-stone-500">{t("Includes cards due now")}</span></dt>
          <dd className="text-3xl font-bold tabular-nums text-stone-900">{stats?.due_today_count ?? "—"}</dd>
        </div>
      </dl>
      {summary?.language === language && !summary.stats && <p role="alert" className="mt-3 text-sm text-red-700">{t("Could not load study progress.")} <button type="button" onClick={() => setAttempt((value) => value + 1)} className="font-semibold underline">{t("Try again")}</button></p>}
    </section>

    </div>
  </>;
}
