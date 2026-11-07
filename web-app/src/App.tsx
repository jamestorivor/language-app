import { Link, NavLink, Route, Routes } from "react-router";
import "./App.css";
import AddPodcastCard from "./components/AddPodcast";
import PodcastLibrary from "./components/PodcastLibrary";
import PodcastDetail from "./components/PodcastDetail";
import PodcastSegments from "./components/PodcastSegments";

const links = [
  { to: "/", label: "Home" },
  { to: "/podcasts", label: "My podcasts" },
  { to: "/podcasts/add", label: "Add podcast" },
];

function App() {
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
            Language app
          </Link>
          <nav
            aria-label="Main navigation"
            className="flex flex-wrap items-center gap-1 sm:gap-2"
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
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-5 py-10 sm:px-8 sm:py-14">
        <Routes>
          <Route
            path="/"
            element={
              <section className="max-w-3xl rounded-3xl border border-stone-200 bg-white px-6 py-10 shadow-sm sm:px-12 sm:py-14">
                <p className="text-xs font-bold uppercase tracking-[0.16em] text-emerald-800">
                  Your listening practice
                </p>
                <h1 className="mt-4 text-4xl font-bold tracking-tight text-stone-950 sm:text-5xl">
                  Learn with podcasts.
                </h1>
                <p className="mt-5 max-w-xl text-base leading-7 text-stone-600 sm:text-lg">
                  Practice listening with your podcasts.
                </p>
                <Link
                  to="/podcasts"
                  className="mt-8 inline-block rounded-xl bg-emerald-900 px-5 py-3 text-sm font-semibold text-white transition-colors hover:bg-emerald-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-800"
                >
                  View my podcasts
                </Link>
              </section>
            }
          />
          <Route
            path="/podcasts"
            element={
              <>
                <p className="text-xs font-bold uppercase tracking-[0.16em] text-emerald-800">
                  Your library
                </p>
                <h1 className="mt-3 text-3xl font-bold tracking-tight text-stone-950 sm:text-4xl">
                  My podcasts
                </h1>
                <p className="mt-3 text-base text-stone-600">
                  Choose an episode to continue listening.
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
                    Your library
                  </p>
                  <h1 className="mt-3 text-3xl font-bold tracking-tight text-stone-950 sm:text-4xl">
                    Add a podcast
                  </h1>
                </div>
                <AddPodcastCard />
              </div>
            }
          />
          <Route path="/podcasts/:podcastId" element={<PodcastSegments />} />
          <Route
            path="/podcasts/segments/:segmentId"
            element={<PodcastDetail />}
          />
          <Route
            path="*"
            element={
              <>
                <h1 className="text-3xl font-bold tracking-tight">
                  Page not found
                </h1>
                <Link
                  to="/"
                  className="mt-6 inline-block text-sm font-semibold text-emerald-800 hover:underline"
                >
                  ← Home
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
