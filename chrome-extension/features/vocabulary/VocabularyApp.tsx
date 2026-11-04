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
    async function loadWords() {
      if (parsed) return;

      const tokenList = await parsePageOnLoad();
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
      setParsed(true);
    }

    function handleMessage(message: { type?: string }) {
      if (message.type === PARSE_CURRENT_PAGE_MESSAGE_TYPE) {
        return loadWords().then(() => ({ ok: true }));
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
        onFamiliarityChange={handleFamiliarityChange}
      ></Panel>
    );
  else return null;
}
