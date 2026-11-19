export type StudyShortcuts = {
  show_answer: string;
  again: string;
  hard: string;
  good: string;
  easy: string;
};

export const defaultStudyShortcuts: StudyShortcuts = {
  show_answer: "Enter", again: "a", hard: "s", good: "d", easy: "f",
};

export const shortcutOptions = [
  "Enter", "Space", "ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown",
  ..."abcdefghijklmnopqrstuvwxyz0123456789".split(""),
];

export function shortcutLabel(key: string): string {
  return key.length === 1 ? key.toUpperCase() : key.replace("Arrow", "Arrow ");
}

export function eventShortcut(event: KeyboardEvent): string {
  return event.key === " " ? "Space" : event.key.length === 1 ? event.key.toLowerCase() : event.key;
}
