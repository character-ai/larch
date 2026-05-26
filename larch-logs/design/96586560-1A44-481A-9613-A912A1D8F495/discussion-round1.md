## Decision 1: Bundle items A and B in one PR
- **Question**: Bundle file-disjoint hardening for `get-issue-state.sh` and `tracking-issue-read.sh --sentinel` into one PR, or split?
- **Resolution**: One PR. Both ~3-line case-statement charset validations of the same shape, share a single review focus, no inter-file dependency cost.
- **Source**: user

## Decision 2: Sentinel empty-value handling
- **Question**: For `tracking-issue-read.sh --sentinel`, should the new ISSUE_NUMBER / RUN_ID validation reject empty values or only non-empty malformed values?
- **Resolution**: Empty passes through; only non-empty malformed values reject. Preserves the existing "sentinel unusable → caller falls back to fresh-adopt" recovery path (caller in `implement-bootstrap.sh:434` already AND-chains `valid_issue_number` / `valid_run_id` so a `FAILED=true` envelope falls through to the same "malformed tracking sentinel. Clearing sentinel and re-adopting." recovery branch as before).
- **Source**: user

## Decision 3: Regression harness for get-issue-state.sh
- **Question**: Add a dedicated `test-get-issue-state.sh` harness or fold the new --issue numeric validation tests into `test-implement-bootstrap.sh`?
- **Resolution**: Add a small dedicated `scripts/test-get-issue-state.sh` mirroring the per-script pattern of `test-post-tracking-issue.sh` and `test-slack-issue-announce.sh`. Wire a `test-get-issue-state` Makefile target and add it to one of the `test-harnesses-N` shards (matching where get-issue-state's sibling scripts live).
- **Source**: user

## Decision 4: Caller-side safety analysis
- **Question**: Do the new self-validations introduce any observable behavior change for current callers?
- **Resolution**: No.
  - Item A: `implement-bootstrap.sh:630-633` already does `case "$ISSUE_NUMBER_OPT" in *[!0-9]*|"") die_usage "--issue-number must be numeric" ;; esac` on argv before invoking `get-issue-state.sh --issue "$ISSUE_NUMBER_OPT"` (line 457). Adding self-validation in `get-issue-state.sh` cannot be triggered by current callers.
  - Item B: `implement-bootstrap.sh:434` already AND-chains `valid_issue_number "$sentinel_issue" && valid_run_id "$sentinel_run_id"` before trusting sentinel values; on failure the code falls through to the "malformed tracking sentinel. Clearing sentinel and re-adopting." path (line 450). Adding `FAILED=true` in the sentinel helper for a non-empty malformed value sets `read_failed=true` at line 430, which short-circuits the AND-chain → same recovery path. No observable change.
- **Source**: codebase
