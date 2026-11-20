import { createContext, useContext, useState } from "react";

export type StudyLanguage = "ja" | "en";
export const studyLevels: Record<StudyLanguage, readonly string[]> = {
  ja: ["N5", "N4", "N3", "N2", "N1"],
  en: ["A1", "A2", "B1", "B2", "C1", "C2"],
};
export type StudyLanguageContextValue = {
  language: StudyLanguage;
  levels: Record<StudyLanguage, string | null>;
  chooseLanguage: (value: StudyLanguage) => Promise<boolean>;
  chooseLevel: (language: StudyLanguage, level: string | null) => Promise<boolean>;
  saving: boolean;
  error: boolean;
};
export const StudyLanguageContext = createContext<StudyLanguageContextValue | null>(null);

// A fallback keeps standalone components usable outside the signed-in app.
export function useStudyLanguage() {
  const context = useContext(StudyLanguageContext);
  const [fallback, setFallback] = useState<StudyLanguage>(() => {
    try { return localStorage.getItem("study-language") === "en" ? "en" : "ja"; }
    catch { return "ja"; }
  });
  async function chooseFallback(value: StudyLanguage) {
    setFallback(value);
    try { localStorage.setItem("study-language", value); } catch { /* Storage is optional. */ }
    return true;
  }
  return [context?.language ?? fallback, context?.chooseLanguage ?? chooseFallback] as const;
}
