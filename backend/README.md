1. Sentences are parsed using Suachi.py

2. It returns the tokens of the sentences as `JapaneseTokenizedResponse` and each token has:

- text
- dictionary_form
- katakana_reading
- start_idx
- end_idx
- part_of_speech

3. The tokens are regrouped if necessary into `TokenGroup` which has:

- word_id
- text
- lookup_form
- familiarity_score
- senses
- start_idx
- end_idx
- tokens
- display

### Selection of entry from the DB

_Priority List_

If kanji (spelling) is present

1. Use TokenGroup's lookup_form to try to match the DB's spelling.
2. Of those results, filter those that have the same reading.

If kanji (spelling) is not present

1. Use TokenGroup's tokens readings to search the reading db.
2. Use POS, commoness and context to rank.

Using POS and commonness to rank.

1. Check the matches for the POS between DB entry and TokenGroup.
2. Allocate a score to common entries
3. Sort by the total score that comes from POS matching and commonness

うちに


### Podcast duration lookup

Set `YOUTUBE_API_KEY` for YouTube videos and `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET` for Spotify episodes in the backend environment. `SPOTIFY_MARKET` optionally selects the Spotify market (defaults to `SG`). Episode creation reads duration from provider metadata; it does not download media.

Podcast vocabulary estimates require the latest database migration (`alembic upgrade head`).
Ratings are captured when an episode's transcript is added. Existing episodes get a dated
baseline the first time their vocabulary is viewed. Replacing a transcript, changing its
language, or rebuilding segments starts a new baseline. Estimates use matched transcript
vocabulary and do not measure listening comprehension or grammar.
Episode added dates are recorded for new episodes; older episodes show the date as
unavailable because it was not previously stored.
