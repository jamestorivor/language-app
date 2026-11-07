import { useId } from "react";
import "./RatingScale.css";

type RatingScaleProps = {
  value: number | null;
  onChange: (score: number) => void;
};

function RatingScale({ value, onChange }: RatingScaleProps) {
  const groupName = useId();
  return (
    <fieldset className="rating-scale" aria-label="Familiarity">
      <div className="rating-scale-options">
        {[1, 2, 3, 4, 5].map((score) => (
          <label className="rating-scale-option" key={score}>
            <input
              className="rating-scale-input"
              type="radio"
              name={groupName}
              value={score}
              checked={value === score}
              onChange={() => onChange(score)}
              aria-label={`Familiarity ${score} of 5`}
            />
            <span className="rating-scale-button">{score}</span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}

export default RatingScale;
