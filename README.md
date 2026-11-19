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
dictionary data, and the latest migrations before use. Podcast metadata lookup also
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

## Clerk authentication

Create a Clerk application and configure the desired sign-in methods in its dashboard.
Set `VITE_CLERK_PUBLISHABLE_KEY` in the web app build environment. The backend
requires `CLERK_AUTHORIZED_PARTIES`, a comma-separated list of exact allowed
frontend origins (for example `http://localhost:5173,https://your-app.example`),
and either `CLERK_JWT_KEY` (the Clerk JWT public key, with literal `\n` in place
of line breaks) or `CLERK_SECRET_KEY` for fetching verification keys. Keep the
secret key on the server. Use keys from the same Clerk instance on both sides.
A local `VITE_API_BASE_URL` can point Vite to the backend origin; deployed builds
should normally use the same-origin API. If the web app is hosted on another
origin, add it to the backend CORS allowlist in `backend/app/main.py` too.

Run `uv sync` and `uv run alembic upgrade head` from `backend` before starting
the updated application. Clerk handles sign-up, sign-in, and sign-out; every API
request carries a short-lived session token verified by the backend. The first
request creates a local user linked to the Clerk user ID. Podcasts, vocabulary,
study cards, and settings are scoped to that user.

Existing data belonging to the former development user remains in the database,
but is not automatically assigned to a new account. To retain it, back up the
database, find the intended Clerk user ID in the Clerk dashboard, and link the
old user row to that ID **before the account first makes an API request**. For
example, on the intended database, use a parameterized SQL client to set
`users.clerk_id` on the old row (normally `id = 1`) to that exact Clerk user ID,
only after verifying the row and account are correct. The unique constraint
prevents the same Clerk ID being linked twice. If the new account has already
created a local row, a separate data migration is needed; do not delete either
row without reconciling its data.

### Browser extension

Enable the Native API in the Clerk dashboard. Configure the extension build with
`WXT_CLERK_PUBLISHABLE_KEY` (the same Clerk instance),
`WXT_CLERK_FRONTEND_API` (the full Frontend API URL from Clerk), and
`WXT_API_BASE_URL` (the backend URL ending in `/`, including `/api/` if needed).
The build adds these hosts to its permissions. Sign in through the extension
popup with a method supported by Clerk's popup flow; this is a separate session
from the web app. The backend's `CLERK_AUTHORIZED_PARTIES` must also include the
extension's exact `chrome-extension://<extension-id>` origin if that is the
session token's authorized party. Use `WXT_EXTENSION_PUBLIC_KEY` to keep a
stable extension ID and register it in Clerk as required. Reload the extension
after changing build settings. See [Clerk's extension setup](https://clerk.com/docs/chrome-extension/getting-started/quickstart)
and [session token documentation](https://clerk.com/docs/guides/sessions/session-tokens).

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
scores and are saved to the signed-in account.

To change a podcast's segment length, open its segments page and select **Edit
podcast details**. Enter a new length in minutes and save. The app rebuilds all
segments; existing segment links may change. If the podcast has transcript text,
upload a timestamped UTF-8 `.txt` transcript (one timestamped line per entry),
or select current YouTube captions for a YouTube episode. Transcripts saved
before caption timings were preserved do not have the timestamps needed for
precise navigation or redistribution.

### Podcast vocabulary coverage

The vocabulary estimate counts repeated occurrences of lexical groups in the
available transcript. Ratings 3–5 count as provisionally known; ratings 0–2
and unmatched groups are uncertain. The lower bound is the share provisionally
known, and the upper bound assumes every uncertain group is known. These are
assumption-based bounds, not a confidence interval or a listening-comprehension
score. Since no rating explicitly means that a word is unknown, the upper bound
is currently 100%. Expressions and conjugated forms can count as one group;
Japanese and English tokenization differs, so the estimate is not directly
comparable to published all-word coverage thresholds or between languages.
Matched groups hidden in the transcript, including Japanese particles, are
included in the estimate. The baseline uses the same calculation with ratings
captured when the transcript was added or replaced; for older episodes, the
baseline is captured on first analysis.

The backend's Vercel build runs `scripts/strip_debug_symbols.py` after installing
dependencies. This removes debug symbols from the Linux NLP libraries while
keeping both parser models and dictionaries intact, and updates the package
metadata Vercel uses to calculate bundle size. The build image needs GNU
`strip`; a custom Vercel build command must run this script after dependency
installation. Development tools, including Alembic and pytest, are installed
with the default `uv sync` but excluded from production dependencies.
The Linux spaCy wheels are pinned as direct sources so Vercel bundles the
stripped package instead of downloading the full wheel during a cold start.
The application uses Sudachi's full dictionary, which requires more disk space
than the core dictionary during installation.
When upgrading spaCy, update its version and Linux wheel URLs together, then
regenerate `backend/uv.lock`.

## Marking vocabulary as known by level

On the home page, select Japanese (JLPT) or English (CEFR) and a level to set
matching dictionary entries at that level and easier levels to familiarity 5.
This replaces any existing ratings for those entries; words without a matching
level are left alone. The levels are approximate, and word-level ratings do not
distinguish individual meanings. JLPT lists are unofficial.

For an existing installation, run `uv run alembic upgrade head` from `backend`
after updating the application. The migration adds and populates levels for
existing dictionaries; later dictionary imports assign levels to new entries.
Import the English dictionary as described above and, from `backend`, run
`uv run python -m app.db.import_jap_dictionary` to import the included JMdict
data. Importing is necessary before the feature can mark words. Familiarity updates
are saved to the signed-in account.

The bundled Japanese level mapping is derived from [OpenJLPT](https://github.com/evanclan/OpenJLPT),
which uses JMdict and KANJIDIC2 (EDRDG), Jonathan Waller's JLPT lists, and
Tatoeba; it is distributed under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).
See `backend/app/data/openjlpt-NOTICE.md` and `openjlpt-LICENSE` for attribution
and license details. The mapping retains JMdict IDs and the easiest listed level.

## Sentence study

Select a Japanese word in a podcast transcript and choose **Add to Study** to
save its sentence as a study card. Different sentences for the same word have
independent cards and FSRS schedules. Opening words, looking up definitions, changing ratings,
and marking vocabulary known by level do not add cards. If the word was marked
“Won’t learn,” adding it clears that status and leaves it unrated; other
familiarity ratings are unchanged by adding. Review grades are separate from
the familiarity scale.

Reviews can automatically advance familiarity: the first successful recall
advances level 1 to 2; level 2 advances after successful recalls on three UTC
dates and at least seven days of stability; level 3 advances after five UTC
dates and at least 30 days of stability. Hard, Good and Easy count as successful
recalls. Again lowers levels 3–4 to 2, or level 2 to 1. Explicit familiarity
choices remain recorded separately and can be changed at any time; later
reviews can update the effective level. Level 5 is only set manually.

Levels 1–2 use FSRS's retention scheduling (90% by default). Study settings
let you change the retention target, maximum FSRS interval and review spreading.
Changes apply at each card's next review; existing due dates remain unchanged.
Once a card at level 3 or 4
reaches the review phase, its next review becomes eligible when FSRS predicts
80% recall, which can be later than the maximum FSRS interval; learning and
relearning steps retain their usual timing. Level 5
and “Won’t learn” suspend automatic reviews until familiarity is changed.
Removing a card from study keeps its schedule, history and occurrence for a
later explicit re-add. Familiarity is shared by a word's cards, while each
card retains its own schedule and review history.

Existing installations need `uv sync` and `uv run alembic upgrade head` from
`backend` before using study. A saved sentence keeps its text and selected word
even if the transcript is later edited or the card is removed from Study.
Open its source from the answer or the Study List; the Removed filter provides
access to removed cards without re-enrolling them. You can switch between
saved sentences for the same word. Newly imported timestamped captions retain
cue times: YouTube context playback starts at the first relevant cue, which
can cover more than the selected sentence. Older or untimed transcripts show
an unavailable timestamp instead of an estimate. Refreshing YouTube captions
or replacing a transcript with timestamped text may restore navigation when
the saved sentence can be matched unambiguously. Playback in the app currently
supports YouTube only. Study data is saved to the signed-in account.

The English mapping is derived from [Open Language Profiles](https://github.com/vitwits/english-wordlist-cefr-a1-c2):
The CEFR-J Wordlist Version 1.5, compiled by Yukio Tono, Tokyo University of
Foreign Studies (retrieved from http://www.cefr-j.org/download.html on January
20, 2020), and the Octanove Vocabulary Profile C1/C2 version 1.0 by Octanove
Labs, licensed under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).
The mapping keeps headwords and the easiest level across parts of speech; exact
normalized headwords are matched to EJDict. Both mappings omit entries that do
not match the installed dictionaries.

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
