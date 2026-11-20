export function learningLanguageFromProfile(profile: unknown): "ja" | "en" {
  if (!profile || typeof profile !== "object") throw new Error("Invalid learning language");
  const data = profile as { onboarding_required?: unknown; learning_language?: unknown };
  if (data.onboarding_required === true) throw new Error("Complete setup on the website before parsing a page.");
  if (data.learning_language !== "ja" && data.learning_language !== "en") throw new Error("Invalid learning language");
  return data.learning_language;
}
