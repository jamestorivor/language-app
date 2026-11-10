import { useState } from "react";
import { API_BASE_URL } from "../api/config";
import { loggedFetch } from "../api/client";

type Language = "ja" | "en";
const levels: Record<Language, string[]> = {
  ja: ["N5", "N4", "N3", "N2", "N1"],
  en: ["A1", "A2", "B1", "B2", "C1", "C2"],
};

export default function MarkKnown() {
  const [language, setLanguage] = useState<Language>("ja");
  const [level, setLevel] = useState("N5");
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

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
        ? "No matching words were found. Make sure the dictionary and level data have been imported."
        : `Marked ${result.matched_words.toLocaleString()} words as known.`);
    } catch {
      setError("Could not update your words. Please try again.");
    } finally {
      setPending(false);
    }
  }

  return (
    <section className="mt-6 max-w-3xl rounded-3xl border border-stone-200 bg-white px-6 py-8 shadow-sm sm:px-12">
      <h2 className="text-xl font-bold tracking-tight text-stone-950">Mark words you already know</h2>
      <p className="mt-2 text-sm leading-6 text-stone-600">
        Set words at the selected level and easier levels to 5. This also changes existing ratings for those words.
        Level lists are approximate and do not cover every word.
      </p>
      <form onSubmit={submit} className="mt-5 flex flex-wrap items-end gap-4">
        <label className="flex flex-col gap-1.5 text-sm font-medium text-stone-700">
          Language
          <select value={language} disabled={pending} onChange={(event) => {
            const next = event.target.value as Language;
            setLanguage(next);
            setLevel(levels[next][0]);
            setMessage("");
            setError("");
          }} className="rounded-lg border border-stone-300 bg-white px-3 py-2 text-stone-900">
            <option value="ja">Japanese</option>
            <option value="en">English</option>
          </select>
        </label>
        <label className="flex flex-col gap-1.5 text-sm font-medium text-stone-700">
          {language === "ja" ? "JLPT level" : "CEFR level"}
          <select value={level} disabled={pending} onChange={(event) => { setLevel(event.target.value); setMessage(""); setError(""); }} className="rounded-lg border border-stone-300 bg-white px-3 py-2 text-stone-900">
            {levels[language].map((item) => <option key={item} value={item}>{item}</option>)}
          </select>
        </label>
        <button disabled={pending} className="rounded-lg bg-emerald-900 px-4 py-2.5 text-sm font-semibold text-white hover:bg-emerald-800 disabled:opacity-50">
          {pending ? "Updating…" : "Mark as known"}
        </button>
      </form>
      {message && <p role="status" className="mt-4 text-sm text-emerald-800">{message}</p>}
      {error && <p role="alert" className="mt-4 text-sm text-red-700">{error}</p>}
    </section>
  );
}
