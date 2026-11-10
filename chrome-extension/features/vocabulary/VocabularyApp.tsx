import { useEffect, useState } from "react";
import type { TokenGroup } from "@/contracts/parse-japanese";
import type {
  LocalJapStorage,
  UpdateFamiliarityScoreResponse,
} from "@/contracts/jap-vocab";
import Panel from "./panel/Panel";
import { requestWordFamiliarityUpdate } from "@/messaging/jap-vocab";
import type { UpdateFamiliarityScoreData } from "@/contracts/jap-vocab";
import { parsePageOnLoad } from "./proces-page";
import { get_familiarity_css_class } from "./bound-words";
import { PARSE_CURRENT_PAGE_MESSAGE_TYPE } from "@/contracts/content-messages";

export default function VocabularyApp() {
  const [japVocabStore, setJapVocabStore] = useState<LocalJapStorage>({});
  const [parsed, setParsed] = useState(false);
  const [language, setLanguage] = useState<"ja" | "en">("ja");

  function updateSpanCssFamiliarity(wordId: number, newScore: number) {
    const spans = document.querySelectorAll(`span[data-word-id="${wordId}"]`);
    for (const span of spans) {
      span.classList.remove(
        "unfamiliar",
        "familiarity-1",
        "familiarity-2",
        "familiarity-3",
        "familiarity-4",
        "familiarity-5",
      );
      span.classList.add(get_familiarity_css_class(newScore));
    }
  }

  async function handleFamiliarityChange(wordId: number, newScore: number) {
    const data: UpdateFamiliarityScoreData = {
      word_id: wordId,
      new_score: newScore,
      language,
    };
    const result = await requestWordFamiliarityUpdate(data);

    setJapVocabStore((previous: LocalJapStorage) => {
      const word = previous[wordId];
      if (!word) return previous;

      return {
        ...previous,
        [wordId]: {
          ...word,
          familiarity_score: result.response.new_score,
        },
      };
    });
    updateSpanCssFamiliarity(wordId, newScore);
  }

  useEffect(() => {
    async function loadWords(selectedLanguage: "ja" | "en") {
      if (parsed) return false;

      const tokenList = await parsePageOnLoad(selectedLanguage);
      const storage: LocalJapStorage = {};
      console.log(`length of tokenlist passed to react : ${tokenList.length}`);
      for (const token of tokenList) {
        const wordId = token.word_id;
        if (wordId) {
          storage[wordId] = token;
        }
      }
      console.log(storage);
      setJapVocabStore(storage);
      setLanguage(selectedLanguage);
      setParsed(true);
      return true;
    }

    function handleMessage(message: { type?: string; language?: "ja" | "en" }) {
      if (message.type === PARSE_CURRENT_PAGE_MESSAGE_TYPE) {
        return loadWords(message.language === "en" ? "en" : "ja")
          .then((ok) => ({ ok, error: ok ? undefined : "Reload the page to change language." }))
          .catch(() => ({ ok: false, error: "Could not parse the page. Check the backend and reload the page." }));
      }
      return undefined;
    }

    browser.runtime.onMessage.addListener(handleMessage);
    return () => browser.runtime.onMessage.removeListener(handleMessage);
  }, [parsed]);

  if (parsed)
    return (
      <Panel
        localJapDb={japVocabStore}
        language={language}
        onFamiliarityChange={handleFamiliarityChange}
      ></Panel>
    );
  else return null;
}
