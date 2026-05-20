## Goal
Commit scout artifacts to round-N so scout firing is auditable from larch-logs

## Implementation Plan
## Goal
Commit scout artifacts to round-N larch-logs so scout firing is auditable from committed run history (issue #2356).


### Part A — Allow-list scout files in `round_artifact_included()`
File: `scripts/larch-log.sh`, line 92 pattern list.
Add `scout-round*-status.env|scout-round*-manifest.json` to the glob pattern case.
Rationale: both files are round-scoped (round number in the name) so globs are correct per the issue.

### Part B — Walk `dynamic-archetypes/` in `write-round` + allow-list its files
1. File: `scripts/larch-log.sh`, line 92 — add `reviewer-dyn-*.md|dyn-*-prompt.md` to the pattern list.
2. File: `scripts/larch-log.sh`, line 299 — replace the single `find -maxdepth 1` with a grouped command that also walks `$SOURCE_DIR/dynamic-archetypes` when present, then pipes all results through `LC_ALL=C sort`. Flatten to round root via `basename "$src"` (already done by the loop).

### Part C — Wire `/implement` to flush `review-scout-manifest` batch
File: `skills/review-and-fix/scripts/review-and-fix.sh`.
After `flush_round_log_after_coder` at line 1094, inside `run_implement_round()`:
- Read `SCOUT_STATUS` from `$core_out` via `kv_get`; default to `na`.
- When non-`na` and `RUN_ID` and `LARCH_LOG_SH` are set: read `DYNAMIC_SLOTS` and `SCOUT_MANIFEST` from `$core_out`, assemble a `review-scout-manifest` JSON payload with `jq -cn`, write via `larch-log.sh write --batch review-scout-manifest`, use `append_log_write_failure` on error. This mirrors the `/review` path in `skills/review/SKILL.md:59`.

### Regression tests

**test-larch-log.sh** (5 new tests in the write-round section):
1. Scout status file committed: fixture round-dir with `scout-round1-status.env` → assert committed.
2. Scout manifest committed: fixture with `scout-round1-manifest.json` → assert committed.
3. Dynamic-archetypes flattened: fixture `dynamic-archetypes/reviewer-dyn-api.md` + `dyn-api-prompt.md` → assert both appear in round root.
4. No-regression (no scout files): clean fixture → same files committed as before.
5. Denied files stay denied: `cursor-specialist-correctness-output.txt` → assert excluded.

**test-review-and-fix.sh** (2 new tests):
6. Scout summary committed in /implement: stub `review-core.sh` to emit `SCOUT_STATUS=ok DYNAMIC_SLOTS=2 SCOUT_MANIFEST=<path>`; run in implement mode; assert `review-scout-manifest.json` committed with correct JSON.
7. No commit when scout=na: stub emits `SCOUT_STATUS=na`; assert NO `review-scout-manifest.json` at run root.


## Test plan
- Run `make lint` (includes `make lint-bash32`) after edits.
- Run `scripts/test-larch-log.sh` directly — new tests pass, no regressions.
- Run `skills/review-and-fix/scripts/test-review-and-fix.sh` — new tests pass.
