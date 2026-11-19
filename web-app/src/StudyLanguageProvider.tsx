import { useEffect, useRef, useState, type ReactNode } from "react";
import { loggedFetch } from "./api/client";
import { API_BASE_URL } from "./api/config";
import { useLanguage } from "./i18n-context";
import { StudyLanguageContext, type StudyLanguage } from "./utils/studyLanguage";

export function StudyLanguageProvider({ children }: { children: ReactNode }) {
  const { t } = useLanguage();
  const [language, setLanguage] = useState<StudyLanguage | null>(null);
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
      if (active) setLanguage(profile.learning_language);
    }).catch(() => { if (active) setLoadError("unavailable"); });
    return () => { active = false; };
  }, [attempt]);

  async function chooseLanguage(next: StudyLanguage) {
    if (savingRef.current) return false;
    if (next === language) return true;
    savingRef.current = true;
    setSaving(true);
    setSaveError(false);
    try {
      const response = await loggedFetch("profile.update", new URL("profile", API_BASE_URL), {
        method: "PUT", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ learning_language: next }),
      });
      if (!response.ok) throw new Error("Could not save profile");
      setLanguage(next);
      return true;
    } catch { setSaveError(true); return false; }
    finally { savingRef.current = false; setSaving(false); }
  }

  if (loadError) return <main className="p-8" role="alert">{t(loadError === "configuration" ? "The server is not configured for sign-in. Check the backend authentication settings and restart it." : "Could not load your learning language.")} <button className="underline" onClick={() => setAttempt((value) => value + 1)}>{t("Try again")}</button></main>;
  if (!language) return <p className="p-8" role="status">{t("Loading your profile…")}</p>;
  return <StudyLanguageContext.Provider value={{ language, chooseLanguage, saving, error: saveError }}>
    {children}
  </StudyLanguageContext.Provider>;
}
