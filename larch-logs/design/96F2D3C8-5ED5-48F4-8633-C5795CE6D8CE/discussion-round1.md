# Round 1 — Scope decisions (issue #4900)

## Decision 1: Primary fix approach for the committed outcome token
- **Question**: For a healthy run about to create its PR (and will merge), what target outcome should the committed final-summary/manifest record instead of terminal `bailed`?
- **Resolution**: Neutral non-terminal token (issue fix #2). Record a success-classified non-terminal token (e.g. `pr-created`) instead of terminal `bailed`. The authoritative `merged` record stays on the GitHub tracking issue. No speculative pre-squash `merged` write and no rollback. Do NOT implement fix #1 (speculative merged flush).
- **Source**: user

## Decision 2: Reach beyond the writer (historical data + downstream tooling)
- **Question**: How far should the fix reach beyond the run-log writer for already-corrupted historical dirs?
- **Resolution**: Fix-forward AND add audit tolerance (issue fix #4). Fix the writer so new runs are correct, and make the committed-log classifiers treat a merged-PR dir as merged despite a stale token. Do NOT backfill/rewrite existing committed run-log dirs (that mutates committed history and is adjacent to NEVER #16).
- **Source**: user

## Decision 3: Serialization with in-flight overlapping issues
- **Question**: #4877 (`[DESIGNING]`) also edits `python/ship.py`; #4878 (`[DESIGNING]`) also edits `python/stall_recovery.py`. Wire native blocked-by edges?
- **Resolution**: Wire #4900 blocked-by #4877 only (ship.py is the likely conflict surface). Skip the #4878 edge (stall_recovery.py regions are disjoint). Wire and verify this edge during finalize.
- **Source**: user

## Decision 4: Companion manifest reconciliation (issue fix #3) — in-scope by default
- **Question**: Is the manifest `steps_ran.step8` / `status=partial` reconciliation required?
- **Resolution**: In-scope. With Approach #2 the outcome becomes `pr-created` (not `merged`), so `_stamp_skipped_steps_for_terminal_report` still runs and can stamp `step8=false` → `status=partial`. The committed manifest must be consistent with on-disk reality (a present `final-summary.md` must never be stamped `step8=false`). Treated as a required companion, not a separate user gate.
- **Source**: codebase / issue (fix #3 "likely-required companion")

## Hard constraints (must not break)
- **NEVER #16** in `skills/implement/SKILL.md`: never commit larch run logs after the PR merges. No post-merge commit, no reintroduction of `LARCH_LOG_COMMIT_POSTMERGE_SHIP_PR`. The fix is pre-merge only.
- The live end-of-run summary and the GitHub tracking-issue comment already render `merged` correctly. Do not regress them.
- Genuine bails (no PR created) must still record `bailed` — the neutral token applies only to the pre-terminal snapshot where the run is healthy and a PR exists / is imminent.
