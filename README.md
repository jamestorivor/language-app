# language-app

This application is aimed at Japanese learners who are trying to do more extensive reading, to allow them to keep track of words that they have come accross.

## Project Status

This project is under development.

The vocabulary panel should stay open when the page scrolls or the window resizes. Dismiss it by clicking outside the panel or pressing Escape.

## Vercel services

The root `vercel.json` routes `/api/*` to the FastAPI service and all other
paths to the Vite service. Browser requests use the same-origin `/api/` path;
there are no server-to-server calls between these services and therefore no
service bindings. The frontend's `vercel.json` provides the single-page app
fallback for direct links and refreshes. Existing unprefixed backend routes are
retained for local and extension clients.

Select **Services** as the Vercel project framework and configure `DATABASE_URL`
with a reachable PostgreSQL database. Provision the existing schema, Japanese
dictionary data, and development user before use. Podcast metadata lookup also
uses `YOUTUBE_API_KEY` for YouTube, or `SPOTIFY_CLIENT_ID` and
`SPOTIFY_CLIENT_SECRET` for Spotify (`SPOTIFY_MARKET` is optional). Run
`vercel dev` from the repository root to test both services together.

The backend currently uses a fixed development user and does not authenticate
API requests. Protect the deployment or add authentication before exposing real
user data. A local `VITE_API_BASE_URL` can point the Vite development server to
the backend origin; deployed builds should use the default same-origin API.

## Planned features

1. Select and save : Select a Japanese word and save the word to your seen db.
2. Familiarity rating: assign a score of 1-5, with unrated as a seperate state.
3. Word definition (May delegate to a different application)
4. Save context: Allows the ability to revist how the word was actually used.
5. Vocab dashboard (FUTURE)
6. Export and Import (FUTURE)
