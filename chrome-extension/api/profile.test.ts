import { describe, expect, it } from "vitest";
import { learningLanguageFromProfile } from "./profile";

describe("extension learning language", () => {
  it("requires new accounts to finish setup before parsing", () => {
    expect(() => learningLanguageFromProfile({ learning_language: "ja", onboarding_required: true })).toThrow("Complete setup on the website");
  });

  it("uses the saved language after setup", () => {
    expect(learningLanguageFromProfile({ learning_language: "en", onboarding_required: false })).toBe("en");
    expect(learningLanguageFromProfile({ learning_language: "ja", onboarding_required: false })).toBe("ja");
  });
});
