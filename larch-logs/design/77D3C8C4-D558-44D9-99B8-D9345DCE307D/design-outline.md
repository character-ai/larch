## Proposed Design Outline

### Goals
- Neutralize reviewer attribution in voter-facing and MAV-facing ballots across all three voting paths (`/design` plan review, `/review` and `/implement` Step 5 code review) so a voter cannot see which vendor proposed a finding.
- Keep proposer attribution out of band in a `proposer-map.tsv` sidecar so scoring, classification, and accepted/rejected/OOS artifacts stay unchanged.

### Non-goals
- No body-text scrubbing: leave `Codex` / `Cursor` / `Claude` references in finding/OOS bodies untouched.
- No empirical self-vs-other YES-rate measurement (follow-up comment only).
- No change to voting thresholds, `no self-voting exclusion`, or competition scoring math.

### Approach sketch
- Add shared helpers in `python/voting.py` beside `reviewer_for_block` (kept unchanged): neutralize the `- **Reviewer**:` value to `anonymous`, build/read a proposer map, restore attribution for post-vote artifacts.
- `/design`: neutralize `ballot.txt` and write `proposer-map.tsv` before `plan-review voter-dispatch` (in `python/plan_review_round.py`); pass `--proposer-map-file` to `plan-review tally`.
- `/review` + `/implement` Step 5: neutralize the round `findings.md` and write `proposer-map.tsv` after collect/aggregate/prune, before `agent dispatch-voters` (in `python/review_pipeline.py`); pass `--proposer-map-file` to every `review tally-code-votes`.
- Tally reads the proposer map for scoring/classification and restores reviewer lines for artifacts; falls back to `reviewer_for_block` when the sidecar is absent. Sidecar write failure is a hard error before dispatch.

### Surfaces in scope
- Code: `python/voting.py`, `python/plan_review_round.py`, `python/plan_review_tally.py`, `python/review_pipeline.py`, `python/review_tally.py`.
- Docs/skills: `skills/shared/voting-protocol.md`, `docs/voting-process.md`, `docs/point-competition.md`, `skills/design/references/plan-review.md`, `skills/review/SKILL.md`, `skills/implement/references/step5-review-branches.md`.
- Tests: `python/test_voting.py`, `python/test_plan_review.py`, `python/test_review_tally.py`, `python/test_review_pipeline.py`, `python/test_agent_voters.py`.

### Open questions
- None. Strip method is the neutral token `anonymous` (keep the line); all scope settled by Round 1 plus the preserved Q&A decisions.
