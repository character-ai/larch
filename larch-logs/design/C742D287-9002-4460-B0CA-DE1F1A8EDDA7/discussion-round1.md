## Decision 1: Fix replay surfaces (not document-only)
- **Question**: Make classification-replay surfaces apply the sole-finder bonus, or accept/document the divergence?
- **Resolution**: Fix. Make replay surfaces apply the same `LARCH_UNIQUE_FINDER_BONUS` the live tally applies, so replayed scores match the live run.
- **Source**: user

## Decision 2: Both replay surfaces in scope
- **Question**: Fix both replay surfaces, or only the live-consumed one?
- **Resolution**: Both. `python/progress_report.py` Top-reviewers (live, in committed progress reports) AND the `python/voting.py` `scoreboard` CLI verb (`voting scoreboard`, registered in `cli.py:358`, no current workflow callers).
- **Source**: user

## Decision 3: Off-by-default semantics preserved (hard constraint)
- **Question**: Must behavior stay unchanged when the bonus env var is unset?
- **Resolution**: Yes. `LARCH_UNIQUE_FINDER_BONUS` is off by default. When unset/zero/invalid, `unique_finder_bonus_from_env` returns 0.0 and the replay surfaces must produce byte-identical output to today. Zero regression to existing committed run-log replays.
- **Source**: codebase (`python/voting.py:459`) + user direction

## Decision 4: Sole-finder definition mirrors live tally (scope boundary)
- **Question**: What qualifies for the bonus during replay?
- **Resolution**: Exactly the live-tally rule (`plan_review_tally.py:630`): accepted, in-scope (`kind == finding`, not OOS), and exactly one proposing reviewer (`len(reviewers) == 1`). Deduplicated multi-reviewer findings and all OOS rows get no bonus. Replay surfaces already split the reviewer column, so they have the reviewer count.
- **Source**: codebase

## Decision 5: Out of scope
- **Question**: What is explicitly out of scope?
- **Resolution**: The JSONL Top-reviewers path (`_top_reviewers`, "by suggestions accepted") is a count-based ranking, not a point replay, so the bonus does not apply there. No change to the live tally code. No change to the bonus value, default, or env-var contract.
- **Source**: codebase
