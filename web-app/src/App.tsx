import { useLanguage } from "./i18n-context";
import { Link, NavLink, Route, Routes } from "react-router";
import "./App.css";
import AddPodcastCard from "./components/AddPodcast";
import PodcastLibrary from "./components/PodcastLibrary";
import PodcastDetail from "./components/PodcastDetail";
import PodcastSegments from "./components/PodcastSegments";
import Home from "./components/Home";
import UserSettings from "./components/UserSettings";
import Study from "./components/Study";
import StudyHome from "./components/StudyHome";
import StudyList from "./components/StudyList";
import StudySettings from "./components/StudySettings";
import BackButton from "./components/BackButton";



function App() {
  const { t } = useLanguage();
  const links = [
    { to: "/", label: t("Home") },
    { to: "/podcasts", label: t("My podcasts") },
    { to: "/study", label: t("Study") },
    { to: "/podcasts/add", label: t("Add podcast") },
  ];
  return (
    <div className="min-h-screen bg-[#f7f7f4] text-stone-900">
      <header className="border-b border-stone-200/80 bg-white">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-5 py-4 sm:px-8">
          <Link
            to="/"
            className="flex items-center gap-3 text-base font-bold tracking-tight focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-emerald-800"
          >
            <span
              aria-hidden="true"
              className="flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-900 text-lg font-semibold text-white"
            >
              言
            </span>
            {t("Language app")}
          </Link>
          <nav
            aria-label={t("Main navigation")}
            className="order-3 flex w-full flex-wrap items-center gap-1 sm:gap-2 md:order-none md:w-auto"
          >
            {links.map((link) => (
              <NavLink
                key={link.to}
                to={link.to}
                end
                className="rounded-lg px-3 py-2 text-sm font-medium text-stone-600 transition-colors hover:bg-stone-100 hover:text-stone-950 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-800 aria-[current=page]:bg-emerald-50 aria-[current=page]:text-emerald-900"
              >
                {link.label}
              </NavLink>
            ))}
          </nav>
          <NavLink to="/settings" aria-label={t("User settings")} title={t("User settings")} className="inline-flex h-10 w-10 items-center justify-center rounded-full text-stone-600 transition-colors hover:bg-stone-100 hover:text-stone-950 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-800 aria-[current=page]:bg-emerald-50 aria-[current=page]:text-emerald-900">
            <svg aria-hidden="true" viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="8" r="3.5" />
              <path d="M5 20a7 7 0 0 1 14 0" />
            </svg>
          </NavLink>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-5 py-10 sm:px-8 sm:py-14">
        <BackButton />
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/settings" element={<UserSettings />} />
          <Route
            path="/podcasts"
            element={
              <>
                <p className="text-xs font-bold uppercase tracking-[0.16em] text-emerald-800">
                  {t("Your library")}
                </p>
                <h1 className="mt-3 text-3xl font-bold tracking-tight text-stone-950 sm:text-4xl">
                  {t("My podcasts")}
                </h1>
                <p className="mt-3 text-base text-stone-600">
                  {t("Choose an episode to continue listening.")}
                </p>
                <PodcastLibrary />
              </>
            }
          />
          <Route
            path="/podcasts/add"
            element={
              <div className="mx-auto max-w-2xl">
                <div className="text-center">
                  <p className="text-xs font-bold uppercase tracking-[0.16em] text-emerald-800">
                    {t("Your library")}
                  </p>
                  <h1 className="mt-3 text-3xl font-bold tracking-tight text-stone-950 sm:text-4xl">
                    {t("Add a podcast")}
                  </h1>
                </div>
                <AddPodcastCard />
              </div>
            }
          />
          <Route path="/podcasts/:podcastId" element={<PodcastSegments />} />
          <Route path="/study" element={<StudyHome />} />
          <Route path="/study/review" element={<Study />} />
          <Route path="/study/list" element={<StudyList />} />
          <Route path="/study/settings" element={<StudySettings />} />
          <Route
            path="/podcasts/segments/:segmentId"
            element={<PodcastDetail />}
          />
          <Route
            path="*"
            element={
              <>
                <h1 className="text-3xl font-bold tracking-tight">
                  {t("Page not found")}
                </h1>
                <Link
                  to="/"
                  className="mt-6 inline-block text-sm font-semibold text-emerald-800 hover:underline"
                >
                  {t("← Home")}
                </Link>
              </>
            }
          />
        </Routes>
      </main>
    </div>
  );
}

export default App;
