import { useLanguage } from "../../i18n-context";
import { useId } from "react";
import type { RefObject } from "react";
import "./RatingScale.css";

type RatingScaleProps = {
  value: number | null;
  onChange: (score: number) => void;
  onOpenStudy?: () => void;
  studyButtonRef?: RefObject<HTMLButtonElement | null>;
};



function RatingScale({ value, onChange, onOpenStudy, studyButtonRef }: RatingScaleProps) {
  const { t } = useLanguage();
  const ratings = [
    { score: 1, label: t("Unfamiliar"), description: t("You’ve seen the word before, but it still feels unfamiliar when you read it again.") },
    { score: 2, label: t("Recognized"), description: t("You remember seeing the word, but you haven’t used it in conversation or thought.") },
    { score: 3, label: t("Occasionally used"), description: t("You’re familiar enough to think of the word occasionally and have used it, but rarely.") },
    { score: 4, label: t("Frequently used"), description: t("You use the word often, but don’t yet feel you have a full grasp of it.") },
    { score: 5, label: t("Everyday language"), description: t("The word is part of your everyday vocabulary.") },
  ];
  const groupName = useId();
  return (
    <fieldset className="rating-scale" aria-label={t("Familiarity")}>
      <div className="rating-scale-options">
        {ratings.map(({ score, label, description }) => (
          <label className="rating-scale-option" key={score} title={`${label}: ${description}`}>
            <input
              className="rating-scale-input"
              type="radio"
              name={groupName}
              value={score}
              checked={value === score}
              onChange={() => onChange(score)}
              aria-label={t("{score} of 5 — {label}: {description}", { score, label, description })}
            />
            <span className="rating-scale-button">{score}</span>
          </label>
        ))}
      </div>
      <div className="rating-scale-actions">
        <label className="rating-scale-option rating-scale-skip">
          <input
            className="rating-scale-input"
            type="radio"
            name={groupName}
            value={-1}
            checked={value === -1}
            onChange={() => onChange(-1)}
          />
          <span className="rating-scale-button">{t("Won’t learn")}</span>
        </label>
        {onOpenStudy && <button ref={studyButtonRef} type="button" className="rating-scale-add" onClick={onOpenStudy}>{t("Add to Study")}</button>}
      </div>
      <details className="rating-scale-help">
        <summary>{t("Rating meanings")}</summary>
        <p><strong>{t("0 — Unrated:")}</strong> {t("You haven’t rated the word yet.")}</p>
        <p><strong>{t("Won’t learn:")}</strong> {t("You don’t plan to learn this word.")}</p>
        {ratings.map(({ score, label, description }) => (
          <p key={score}><strong>{score} — {label}:</strong> {description}</p>
        ))}
      </details>
    </fieldset>
  );
}

export default RatingScale;
