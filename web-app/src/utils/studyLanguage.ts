import { useState } from "react";

export type StudyLanguage = "ja" | "en";
const storageKey = "study-language";

export function useStudyLanguage() {
  const [language, setLanguage] = useState<StudyLanguage>(() => {
    try { return localStorage.getItem(storageKey) === "en" ? "en" : "ja"; }
    catch { return "ja"; }
  });
  function chooseLanguage(value: StudyLanguage) {
    setLanguage(value);
    try { localStorage.setItem(storageKey, value); } catch { /* Storage is optional. */ }
  }
  return [language, chooseLanguage] as const;
}
