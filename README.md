# language-app

This application is aimed at Japanese learners who are trying to do more extensive reading, to allow them to keep track of words that they have come accross.

## Project Status

This project is under development.

The vocabulary panel should stay open when the page scrolls or the window resizes. Dismiss it by clicking outside the panel or pressing Escape.

## Vercel services

The root `vercel.json` routes `/api/*` to the FastAPI service and all other
paths to the Vite service. Browser requests use the same-origin `/api/` path;
there are no server-to-server calls between these services and therefore no
service bindings. The frontend service's rewrite provides the single-page app
fallback for direct links and refreshes; `web-app/vercel.json` also supports a
standalone frontend deployment. Existing unprefixed backend routes are
retained for local and extension clients.

Select **Services** as the Vercel project framework and configure `DATABASE_URL`
with a reachable PostgreSQL database. Provision the existing schema, Japanese
dictionary data, and development user before use. Podcast metadata lookup also
uses `YOUTUBE_API_KEY` for YouTube, or `SPOTIFY_CLIENT_ID` and
`SPOTIFY_CLIENT_SECRET` for Spotify (`SPOTIFY_MARKET` is optional). Run
`vercel dev` from the repository root to test both services together.

YouTube captions are fetched through [FreeTranscriptAPI](https://freetranscriptapi.com/docs).
Anonymous requests work without configuration, subject to the provider's
per-IP and shared daily limits. Optionally set `FREETRANSCRIPT_API_KEY` in the
backend environment to use account credits instead; keep the key server-side.
The provider charges a credit for an authenticated lookup even when it fails.
The requested podcast language must be available: fallback captions in another
language are rejected. The former Webshare proxy settings are no longer used.

The backend currently uses a fixed development user and does not authenticate
API requests. Protect the deployment or add authentication before exposing real
user data. A local `VITE_API_BASE_URL` can point the Vite development server to
the backend origin; deployed builds should use the default same-origin API.

## English vocabulary

English reading uses spaCy's small English pipeline for word forms and the
EJDict-hand English-to-Japanese dictionary. On an existing database already at
the Alembic baseline, set `DATABASE_URL` to the intended database, then from
`backend` run:

```sh
uv sync
uv run alembic upgrade head
uv run python -m app.db.import_english_dictionary
```

The migration creates the English dictionary and separate user familiarity
tables. The importer reads the included `data/EJDict.zip` and can be rerun:
it updates existing headwords while preserving their IDs and familiarity, and
does not delete headwords removed from a later source. An alternate EJDict
source archive (containing `src/*.txt`) or UTF-8 tab-separated file can be
passed as an argument. The included archive is from
[EJDict-hand](https://github.com/kujirahand/EJDict), distributed by its
maintainers under CC0; SHA-256:
`28ebeb2596e12a9c98691357b0e88a9888ee5ab6003e626df6373096645fce11`.

Choose a podcast's language when adding it; the library can be filtered by
language and each transcript uses the matching parser automatically. Existing
podcasts default to Japanese; edit their details to correct the language.
Changing the language does not replace an existing transcript. Select English
in the browser extension before parsing an English page. Dictionary alternatives
are separated for display, and EJDict's usage annotations are preserved. Exact contiguous
dictionary expressions are supported; separated phrasal verbs and automatic
sense disambiguation are not currently resolved. Reload an extension page to
change the selected language. English scores are independent of Japanese
scores and, like the existing feature, currently use the fixed development user.

The backend's Vercel build runs `scripts/strip_debug_symbols.py` after installing
dependencies. This removes debug symbols from the Linux NLP libraries while
keeping both parser models and dictionaries intact, and updates the package
metadata Vercel uses to calculate bundle size. The build image needs GNU
`strip`; a custom Vercel build command must run this script after dependency
installation. Development tools, including Alembic and pytest, are installed
with the default `uv sync` but excluded from production dependencies.
The Linux spaCy wheels are pinned as direct sources so Vercel bundles the
stripped package instead of downloading the full wheel during a cold start.
This leaves enough temporary disk space to install Sudachi's core dictionary.
When upgrading spaCy, update its version and Linux wheel URLs together, then
regenerate `backend/uv.lock`.

## Logs

Browser developer tools show API request status, duration, operation, and request ID,
as well as uncaught frontend errors. In Vercel, open the backend runtime logs to
find the same request ID in the structured request logs. Japanese parsing also
reports token counts and time spent in each processing stage. Request bodies,
query strings, and exception messages are not included in these application logs.
Set the backend `LOG_LEVEL` environment variable (for example, `WARNING`) to
reduce log volume; it defaults to `INFO`.

## Planned features

1. Select and save : Select a Japanese word and save the word to your seen db.
2. Familiarity rating: assign a score of 1-5, with unrated as a seperate state.
3. Word definition (May delegate to a different application)
4. Save context: Allows the ability to revist how the word was actually used.
5. Vocab dashboard (FUTURE)
6. Export and Import (FUTURE)
