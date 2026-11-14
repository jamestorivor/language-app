import { useId } from "react";
import "./RatingScale.css";

type RatingScaleProps = {
  value: number | null;
  onChange: (score: number) => void;
};

const ratings = [
  { score: 1, label: "Unfamiliar", description: "You’ve seen the word before, but it still feels unfamiliar when you read it again." },
  { score: 2, label: "Recognized", description: "You remember seeing the word, but you haven’t used it in conversation or thought." },
  { score: 3, label: "Occasionally used", description: "You’re familiar enough to think of the word occasionally and have used it, but rarely." },
  { score: 4, label: "Frequently used", description: "You use the word often, but don’t yet feel you have a full grasp of it." },
  { score: 5, label: "Everyday language", description: "The word is part of your everyday vocabulary." },
];

function RatingScale({ value, onChange }: RatingScaleProps) {
  const groupName = useId();
  return (
    <fieldset className="rating-scale" aria-label="Familiarity">
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
              aria-label={`${score} of 5 — ${label}: ${description}`}
            />
            <span className="rating-scale-button">{score}</span>
          </label>
        ))}
      </div>
      <details className="rating-scale-help">
        <summary>Rating meanings</summary>
        <p><strong>0 — Unseen:</strong> The word hasn’t been recorded or rated yet.</p>
        {ratings.map(({ score, label, description }) => (
          <p key={score}><strong>{score} — {label}:</strong> {description}</p>
        ))}
      </details>
    </fieldset>
  );
}

export default RatingScale;
