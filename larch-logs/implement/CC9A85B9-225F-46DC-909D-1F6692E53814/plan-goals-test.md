## Goal
Preserve TMPDIR execution-issue artifacts and reframe cache-freshness as informational in audit-runs

## Implementation Plan

### Problem 1: Preserve TMPDIR refs in execution-issue bodies (aggregate-findings.sh)

**Files to modify:**
1. `skills/review/scripts/aggregate-findings.sh`
   - Add a helper `committed_ref()` that returns a stable relative reference when SESSION_ENV_PATH is set, falling back to the original FAILURE_LOG path otherwise.
   - For each `append_warning` call containing `See $FAILURE_LOG`:
     - If SESSION_ENV_PATH is set: extract round dir name from REVIEW_TMPDIR basename (e.g., "round-1"), use `round-1/aggregator-validate.stderr` as the committed reference.
     - Update execution-issue body to say `See <round>/aggregator-validate.stderr in the committed run log.` instead of the TMPDIR path.
   - Affected lines: 183 (aggregator-dispatch.stderr), 351 (aggregator-validate.stderr).
   - Line 192: no `See` reference needed (DISPATCH_OK already logged inline).

2. `scripts/larch-log.sh`
   - Add `aggregator-validate.stderr|aggregator-dispatch.stderr` to `is_round_artifact()` function pattern at line 89 (after `voting-tally.md` in the same `case` branch).
   - This ensures write-round commits these files to larch-logs/implement/$RUN_ID/round-N/.

3. `docs/run-logs-required-files.tsv`
   - Add conditional entries for the new round artifacts:
     - `round-*/aggregator-validate.stderr` with condition `exn-agg-validate-fail` (when present = aggregator validation failed)
     - `round-*/aggregator-dispatch.stderr` with condition `exn-agg-dispatch-fail`

### Problem 2: Reframe cache-freshness as informational

**Files to modify:**
4. `.claude/skills/audit-runs/scripts/audit-scan-run.sh`
   - In `scan_cache_freshness()` at line 257-258: change `result: fail` → `result: informational` when `run_version < current_version`.
   - Keep `run_version` and `current_version` fields intact.
   - The `manifest larch_version empty` case (line 252) retains `result: fail` since an empty version is a data quality issue.

5. `.claude/skills/audit-runs/scans.tsv`
   - Update cache-freshness row: change severity from `high` to `low` and update `expected_outcome` to reflect informational nature.

6. `.claude/skills/audit-runs/SKILL.md`
   - Line 99: Update the cache-freshness prose from "Treat `cache-freshness` fail as the version-gap signal" to reflect informational result.
   - Add instruction for top-of-report banner: when any run has `run_version < current_version`, prepend a "Self-deploying lens: runs in this batch were on X; current main is Y." banner to the `## Summary` section.

7. `.claude/skills/audit-runs/scripts/audit-scan-run.md`
   - Update the example NDJSON to show `result: informational` for the cache-freshness case.

### Test augmentation

**File to modify:**
8. `.claude/skills/audit-runs/scripts/test-audit-runs.sh`
   - Test 50 (informational result): stub a run-log with `manifest.json` containing `larch_version: "29.8.62"`, run `audit-scan-run.sh --current-version "34.0.0"`, assert `result=informational` (NOT `fail`), assert `run_version` and `current_version` fields present.
   - Test 51 (same-version pass): same but `larch_version: "34.0.0"`, `--current-version "34.0.0"`, assert `result=pass`.
   - Test 52 (aggregator-stderr round-trip): create a fake REVIEW_TMPDIR, SESSION_ENV_PATH, non-empty `aggregator-validate.stderr`; call `append_warning`-equivalent logic; assert execution-issue body references the committed round path (not TMPDIR).
   - Test 53 (empty-stderr handling): same but zero-byte stderr; assert body references committed path and still mentions the file.
   - Test 54 (cursor-ci other-channel coverage): verify append-tool-failure.sh behavior produces embedded content (no TMPDIR path reference) for a cursor-ci-style failure.

**Edge cases:**
- aggregate-findings.sh without SESSION_ENV_PATH: keep original `See $FAILURE_LOG` behavior (no regression for standalone review).
- write-round: the new artifact names are added to the allowlist pattern, not the skip list.
- The test harness calls `audit-scan-run.sh` directly (it's executable), same pattern as Tests 33/35.
- Bash 3.2 compatible: no associative arrays, use `case` patterns for round-dir extraction.

**Verification:**
- `make relevant-checks` (pre-commit + agent-lint) after implementation.
- Tests 50-54 in test-audit-runs.sh pass.
- No regression in existing tests 23-49.

## Test plan
(no test plan section in plan-file)
