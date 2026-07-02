# Quarterly sentiment rescore — instructions for an AI coding agent

This task is designed to be handed verbatim to an AI coding agent (Claude
Code or similar). Human: just point your agent at this issue and say "do
this". Agent: everything you need is below; work on a branch and open a PR —
do not push to `main`.

## Background

Restaurant reviews get an initial sentiment score from NLTK VADER when they
enter the database (`compute_sentiment.py`, `sentiment_source = 'vader'`).
VADER misreads the irony-heavy prose of professional critics, so once a
quarter an LLM rescoring pass replaces the accumulated VADER scores. The
historical backlog was scored by Claude in July 2026
(`sentiment_source = 'claude'`).

## Task

1. Build the local DB: `./create_db.sh` (restores `reviews.db` from
   `reviews.sql`).
2. Find rows needing rescoring:
   ```sql
   SELECT id, title, url FROM reviews
   WHERE sentiment_source IS NULL OR sentiment_source != 'claude';
   ```
   Expect roughly 10–30 rows (one quarter of weekly reviews).
3. The `text` column is deliberately blank in the committed dump (Guardian
   terms don't allow republishing article bodies). Fetch each review from its
   public `url` and read it. Be polite: sequential fetches, ~1 request/sec,
   no retry storms.
4. Score each review yourself (you are an LLM — read the review, do not
   delegate to VADER) on this scale, calibrated to the overall verdict on the
   restaurant, not the writing's tone:
   - 0.0–0.2 scathing pan
   - 0.2–0.4 negative, wouldn't go back
   - 0.4–0.6 mixed / ambivalent
   - 0.6–0.8 positive, recommends
   - 0.8–1.0 rave
   If a page is paywalled or gone, score from the title alone and note it in
   the PR.
5. Apply scores:
   ```sql
   UPDATE reviews SET sentiment = :score, sentiment_source = 'claude' WHERE id = :id;
   ```
6. Regenerate artefacts: `python generate_map.py` then `./save_db.sh`.
7. Commit `reviews.sql` + `index.html` on a branch, open a PR titled
   "Quarterly sentiment rescore", listing each rescored review with old →
   new score. Close this issue via the PR description.

## Constraints

- Do not add API keys, new dependencies, or trained model artefacts to the
  repo (it is public).
- Do not touch rows already marked `sentiment_source = 'claude'`.
- Keep total Guardian fetches under ~100 per run.
