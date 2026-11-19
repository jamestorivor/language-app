import { useEffect, useState } from "react";
import { loggedFetch } from "../api/client";
import { API_BASE_URL } from "../api/config";
import { useLanguage } from "../i18n-context";

export default function KnownWordCount({ language, refresh = 0, light = false }: {
  language: "ja" | "en"; refresh?: number; light?: boolean;
}) {
  const { t, locale } = useLanguage();
  const [result, setResult] = useState<{ language: string; refresh: number; count: number | null } | null>(null);

  useEffect(() => {
    let active = true;
    const url = new URL("vocabulary/known-count", API_BASE_URL);
    url.searchParams.set("language", language);
    void loggedFetch("get_known_word_count", url).then(async (response) => {
      if (!response.ok) throw new Error("Request failed");
      return response.json() as Promise<{ count: number }>;
    }).then(({ count }) => {
      if (active) setResult({ language, refresh, count });
    }).catch(() => {
      if (active) setResult({ language, refresh, count: null });
    });
    return () => { active = false; };
  }, [language, refresh]);

  const current = result?.language === language && result.refresh === refresh ? result : null;
  return <div className={light ? "mt-4 text-emerald-100" : "mt-4 text-stone-600"}>
    <p className={light ? "text-lg font-bold text-white" : "text-lg font-bold text-emerald-900"}>
      {!current ? t("Loading known words…") : current.count === null ? t("Could not load known words.") : t("{count} known words", { count: current.count.toLocaleString(locale) })}
    </p>
    <p className="mt-1 text-sm">{t("{language} · Words rated 4 or 5", { language: language === "ja" ? "日本語" : "English" })}</p>
  </div>;
}
