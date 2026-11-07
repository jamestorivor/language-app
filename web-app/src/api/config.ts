// Browsers call the public, same-origin API route; Vite has no runtime server
// that could consume a Vercel service binding. The override supports local dev.
const API_BASE_URL = new URL("/api/", import.meta.env.VITE_API_BASE_URL || window.location.origin);

export { API_BASE_URL };
