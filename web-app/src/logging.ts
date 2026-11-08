// Global failures are logged without exception messages, which can contain user data.
window.addEventListener("error", (event) => {
  console.error("Unhandled application error", {
    errorType: event.error instanceof Error ? event.error.name : "UnknownError",
    line: event.lineno,
    column: event.colno,
  });
});

window.addEventListener("unhandledrejection", (event) => {
  console.error("Unhandled promise rejection", {
    errorType: event.reason instanceof Error ? event.reason.name : "UnknownError",
  });
});
