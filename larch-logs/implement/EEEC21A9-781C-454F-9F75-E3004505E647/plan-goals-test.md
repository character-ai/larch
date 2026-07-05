## Goal
Implement issue #6370: [IMPLEMENTING] [OOS] /implement follow-ups: ship-rebase guards, step3 bg-wait timeout dedup, run-report precedence, write-final-report CI, SECURITY marker.

## Implementation Plan
## Plan

## Approach

Use the approved outline as binding scope. `approach-synthesis.txt` is `NO_SKETCHES`, so draft from direct repo inspection only.

Keep the change narrow:
- Fail closed before `ship pre-fix-rebase` emits `NEXT_ACTION=continue`.
- Derive timeout markers from named Python constants.
- Merge execution-issues from both sources when both exist, to avoid dropping entries.
- Add only targeted tests and one CI shard prerequisite.
- Update the SECURITY marker text to match `python/larch/core/redact.py`.

## Files to modify/create

### UPDATED: python/larch/implement/dispatch_ship.py

- Move the phase14 skip decision behind checkout validation and rebase-in-progress checks.
- Treat the phase14 flag as a no-checks-observed reship marker, not a blanket skip.
  - Parse flag contents as KV lines (RESUME_PHASE, REASON).
  - Allow skip only when RESUME_PHASE matches `config.SHIP_PR_RRR_RESUME_PHASE` AND REASON matches an explicit no-checks allowlist (e.g., `mergeStateStatus=DIRTY` or `mergeStateStatus=BEHIND`) and conflict metadata is absent.
  - Reject empty flags, flags with wrong RESUME_PHASE, flags whose REASON does not match the allowlist, and flags that indicate a conflict handoff (e.g., `REASON=postbump-rebase-conflict`).
  - Mirror `_ship_route_phase14_reship_pending` symlink exclusion for the flag file.
  - Route conflict metadata before skip.
- In the existing rebase-in-progress path with conflict metadata:
  - Write ship state through `_ship_pre_fix_write_conflict_state(...)` or equivalent `_write_ship_state(phase="rebase", ...)`.
  - Then patch `.ship-route-exit-handoff.env`.
- Make `_ship_pre_fix_patch_handoff(...)` failure fail closed: return non-zero and do not emit `NEXT_ACTION=`.
- Capture the `rebase.rebase_and_push(...)` result.
  - If it is a `RebaseResult` with `rebased=True`, increment `REBASE_COUNT` by one and persist via `_patch_ship_state_keys`, preserving existing iteration, fix_attempts, and transient_retries fields.
- Clear the `.ship-pre-fix-rebase-ok` sentinel at `ship_pre_fix_rebase_main` entry (unlink, ignore missing) before the guarded path executes.
- Write the `.ship-pre-fix-rebase-ok` sentinel on valid terminals: physical rebase success (NEXT_ACTION=continue from rebase path), allowlisted phase14 skip (PRE_FIX_REBASE_STATUS=skip), and conflict-fix routing. Do not write it on request parse failure, guard failure, or write failure.
- Also update `_write_ship_route_handoff`: when appending `PRE_FIX_REBASE_REQUIRED=true`, unlink the `.ship-pre-fix-rebase-ok` sentinel from `implement_tmpdir` (ignore missing) to clear any stale proof from a prior handoff.

### UPDATED: python/larch/implement/dispatch_commit_route.py

- Replace the hardcoded `15600` Step 3 composite marker timeout with `CHECKS_COMMIT_ROUTE_OUTER_TIMEOUT_MS // 1000`.
- Replace the hardcoded `10800` checks-only marker timeout with `CHECKS_STEP3_BG_WAIT_TIMEOUT_S`.
- Keep the existing comment that distinguishes checks-only from full-route timeout.

### UPDATED: python/larch/implement/dispatch_leg.py

- Expose `_CHECKS_DEADLINE_MS` through a public constant `CHECKS_DEADLINE_MS`.
- Add `CHECKS_STEP3_BG_WAIT_TIMEOUT_S = CHECKS_DEADLINE_MS // 1000`.
- Update `CHECKS_COMMIT_ROUTE_OUTER_TIMEOUT_MS` to use `CHECKS_DEADLINE_MS`.
- Preserve the existing private constant only if backward-compatible tests require it.

### UPDATED: python/larch/implement/implement_dispatch.py

- Re-export any renamed or newly public timeout constants needed by existing tests and callers.

### UPDATED: skills/implement/scripts/run-step-checks.sh

- Replace `TIMEOUT_S=10800` with a value derived from the Python constant at startup.
- Set `PYTHONPATH="$CLAUDE_PLUGIN_ROOT/python"` before the import to ensure the larch package resolves in consumer repos.
- Use an inline Python one-liner: `python3 -c "import sys; sys.path.insert(0, '$CLAUDE_PLUGIN_ROOT/python'); from larch.implement.dispatch_leg import CHECKS_STEP3_BG_WAIT_TIMEOUT_S; print(CHECKS_STEP3_BG_WAIT_TIMEOUT_S)"`.
- Fail closed if the derived value is empty or non-numeric (fall back to the existing integer on import failure).

### UPDATED: skills/implement/SKILL.md

- In both the `ci-fix` and `reship` branch bodies: after `ship pre-fix-rebase` returns `NEXT_ACTION=continue`, add a guard that reads `.ship-pre-fix-rebase-ok` from `$IMPLEMENT_TMPDIR`.
- If `PRE_FIX_REBASE_REQUIRED=true` (from `.ship-route-exit-handoff.env`) and `.ship-pre-fix-rebase-ok` is absent, route to post-driver stall handling (Step 16 with `STALL_TRACKING`, then Step 18). Do not use operator-bail for this mechanical failure.

### MAY_UPDATE: skills/implement/references/ship-pr-exit-matrix.md

- If this reference duplicates the ci-fix/reship branch semantics from SKILL.md, update it to require the `.ship-pre-fix-rebase-ok` sentinel check when `PRE_FIX_REBASE_REQUIRED=true`, or add a note that it defers to the SKILL.md guard.

### UPDATED: python/tests/implement/test_implement_dispatch.py

- Add `assert f"TIMEOUT_S={dispatch_leg.CHECKS_STEP3_BG_WAIT_TIMEOUT_S}\n" in marker_text` to `test_run_step_checks_main_arms_step3_bg_wait_marker`.
- Add regression tests for `ship pre-fix-rebase`:
  - Phase14 flag with RESUME_PHASE matching config + allowed REASON passes checkout/repo guards before skip.
  - Phase14 flag with correct RESUME_PHASE, allowed REASON, but in-progress conflict metadata routes to `conflict-fix`, not skip.
  - Phase14 flag with wrong RESUME_PHASE does not skip.
  - Phase14 flag with disallowed REASON (e.g., `postbump-rebase-conflict`) does not skip.
  - Empty or bare phase14 flag does not skip.
  - Allowlisted phase14 skip writes the sentinel (PRE_FIX_REBASE_STATUS=skip path).
  - Sentinel is cleared at entry; stale sentinel is absent after a new handoff writes `PRE_FIX_REBASE_REQUIRED=true`.
  - Successful `rebase_and_push` with `rebased=True` increments and persists `REBASE_COUNT`.
  - Monkeypatch `_ship_pre_fix_write_conflict_state` to raise: assert `rc != 0` and no `NEXT_ACTION=` in stdout.
  - Monkeypatch `_ship_pre_fix_patch_handoff` to raise: assert `rc != 0` and no `NEXT_ACTION=` in stdout.
  - Allowlisted skip + in-progress rebase + no conflict metadata: assert stall.

### UPDATED: python/tests/implement/test_ship.py

- Update phase14 flag fixtures to use producer-faithful KV content (RESUME_PHASE and REASON fields present).
- Keep `REASON=mergeStateStatus=DIRTY` coverage intact.

### UPDATED: python/larch/report/exec_issue_detail.py

- Change `load_issue_detail_groups(..., prefer_run_dir=True)` to merge both sources when both exist:
  - Parse run-dir NDJSON groups.
  - Parse non-empty tmpdir `execution-issues.md` groups.
  - Merge both group sets so neither source drops entries. When both exist: combine `exec_issues` and `warnings` lists from both sources, deduplicating by display_text if a helper supports it; prefer structured groups over degraded counts.
  - Preserve NDJSON-only fallback when tmpdir markdown is absent or empty.
  - Keep degraded legacy NDJSON behavior unchanged for fallback reads.

### UPDATED: python/larch/report/final_report.py

- Keep `prefer_run_dir=True` calls; the helper semantics change transparently.

### UPDATED: python/tests/report/test_exec_issue_detail.py

- Replace or update `test_load_prefers_run_dir_ndjson_when_requested`.
- Add superset fixtures: tmpdir markdown contains the same entries that were flushed to NDJSON plus newer post-flush entries. Assert combined counts include both committed and post-flush entries.
- Add coverage that empty tmpdir markdown still falls back to run-dir NDJSON.

### UPDATED: python/tests/report/test_final_report.py

- Update `test_write_final_report_counts_committed_ndjson_over_live_log` to reflect merged behavior: when both artifacts exist, both NDJSON entries and newer tmpdir-only entries appear in the summary counts.
- Keep an NDJSON-only fallback test.

### UPDATED: skills/implement/scripts/test-write-final-report.sh

- Revise the dual-artifact test block to expect merged counts when both tmpdir markdown and NDJSON exist.
- Add or retain an NDJSON-only fallback case.
- Assert combined counts include entries from both sources when both exist.

### UPDATED: Makefile

- Update `test-write-final-report` to also invoke `bash skills/implement/scripts/test-write-final-report.sh` under `timing harness-mark`, so the bash harness itself runs in CI alongside the pytest filter.
- Add `test-write-final-report` to exactly one `test-harnesses-N` shard.

### UPDATED: SECURITY.md

- Replace the documented PEM truncation marker with the emitted colon form:
  `[content truncated: unterminated PEM block; tail of body dropped for safety]`

## Edge cases

- A stale phase14 flag on the wrong branch or repo must fail before skip.
- A phase14 flag with an empty body, wrong RESUME_PHASE, or non-allowlisted REASON must not trigger skip.
- A phase14 flag with `REASON=postbump-rebase-conflict` must not trigger skip.
- A rebase already in progress with conflict metadata must route to `conflict-fix`.
- A rebase already in progress without conflict metadata should stall.
- Conflict handoff state writes must be all-or-fail from the user-visible contract point of view.
- `REBASE_COUNT` should increment only for a physical rebase, not for no-op pushes.
- The allowlisted phase14 skip writes `.ship-pre-fix-rebase-ok` so the ci-fix/reship guard does not stall a valid no-checks continuation.
- A new handoff that writes `PRE_FIX_REBASE_REQUIRED=true` must clear any stale `.ship-pre-fix-rebase-ok` sentinel.
- Empty tmpdir `execution-issues.md` should not mask a valid run-dir NDJSON file.
- When tmpdir markdown contains both flushed and post-flush entries, merging with NDJSON must not drop the committed rows.
- When the ci-fix path sees `PRE_FIX_REBASE_REQUIRED=true` but `.ship-pre-fix-rebase-ok` is absent, it routes to stall (Step 16 with STALL_TRACKING), not operator-bail.

## Failure modes

- A stale handoff may resume `ci-fix` or `reship` on the wrong checkout if the sentinel is absent and the ci-fix guard is missing.
- A failed conflict handoff write may emit `NEXT_ACTION=conflict-fix` without durable state if not fail-closed.
- Timeout literals may drift again if one call site keeps `10800` or `15600`.
- CI may still miss the final-report bash harness if `test-write-final-report` is not in exactly one shard.
- Final summaries may drop either committed NDJSON rows or post-flush tmpdir entries if the loader does not merge both sources.

## Testing strategy

Run focused tests only:

- `python3 -m pytest python/tests/implement/test_implement_dispatch.py`
- `python3 -m pytest python/tests/implement/test_ship.py`
- `python3 -m pytest python/tests/report/test_exec_issue_detail.py`
- `python3 -m pytest python/tests/report/test_final_report.py`
- `make test-write-final-report`
- `make test-harness-shards-coverage`

Also run lint for changed Python and shell files:
- `make py-lint`
- `make shellcheck`

## Acceptance

Run focused tests only:

- `python3 -m pytest python/tests/implement/test_implement_dispatch.py`
- `python3 -m pytest python/tests/implement/test_ship.py`
- `python3 -m pytest python/tests/report/test_exec_issue_detail.py`
- `python3 -m pytest python/tests/report/test_final_report.py`
- `make test-write-final-report`
- `make test-harness-shards-coverage`

Also run lint for changed Python and shell files:
- `make py-lint`
- `make shellcheck`

diff_added: 450
diff_deleted: 120
mechanical_churn: false
diff_lines: 570

## Test plan
(no test plan section in plan-file)
