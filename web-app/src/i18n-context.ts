import { createContext, useContext } from "react";
import japanese from "./translations.json";

export type Locale = "en" | "ja";
const translations: Record<string, string> = japanese;
export const LanguageContext = createContext<{ locale: Locale; setLocale: (locale: Locale) => void }>({
  locale: "en", setLocale: () => {},
});

export function useLanguage() {
  const { locale, setLocale } = useContext(LanguageContext);
  return {
    locale,
    setLocale,
    t: (text: string, values: Record<string, string | number> = {}) =>
      (locale === "ja" ? translations[text] ?? text : text)
        .replace(/\{(\w+)\}/g, (match, key: string) => values[key] === undefined ? match : String(values[key])),
  };
}
