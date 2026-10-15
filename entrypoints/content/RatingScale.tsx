function RatingScale() {
  return (
    <div className="flex">
      <div className="flex items-center me-4">
        <input
          id="inline-radio"
          type="radio"
          value="1"
          name="inline-radio-group"
          className="w-4 h-4 accent-blue-600"
        />
        <label
          htmlFor="inline-radio"
          className="select-none ms-2 text-sm font-medium text-heading"
        >
          1
        </label>
      </div>

      <div className="flex items-center me-4">
        <input
          id="inline-2-radio"
          type="radio"
          value="2"
          name="inline-radio-group"
          className="w-4 h-4 accent-blue-600"
        />
        <label
          htmlFor="inline-2-radio"
          className="select-none ms-2 text-sm font-medium text-heading"
        >
          2
        </label>
      </div>

      <div className="flex items-center me-4">
        <input
          id="inline-3-radio"
          type="radio"
          value="3"
          name="inline-radio-group"
          className="w-4 h-4 accent-blue-600"
        />
        <label
          htmlFor="inline-3-radio"
          className="select-none ms-2 text-sm font-medium text-heading"
        >
          3
        </label>
      </div>

      <div className="flex items-center me-4">
        <input
          id="inline-4-radio"
          type="radio"
          value="4"
          name="inline-radio-group"
          className="w-4 h-4 accent-blue-600"
        />
        <label
          htmlFor="inline-4-radio"
          className="select-none ms-2 text-sm font-medium text-heading"
        >
          4
        </label>
      </div>

      <div className="flex items-center me-4">
        <input
          id="inline-5-radio"
          type="radio"
          value="5"
          name="inline-radio-group"
          className="w-4 h-4 accent-blue-600"
        />
        <label
          htmlFor="inline-5-radio"
          className="select-none ms-2 text-sm font-medium text-heading"
        >
          5
        </label>
      </div>
    </div>
  );
}

export default RatingScale;
