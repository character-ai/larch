## Plan

## Approach

Implement the fix in the harness only.

- Replace the direct `stdout_keys_block="$(awk ...)"` assignment with a small Bash 3.2-compatible helper.
- Extract `_DESIGN_LIFECYCLE_STDOUT_KEYS` with awk from the header through the exact frozenset close line `})`.
- Retry extraction up to 3 times.
- Treat a capture as complete only when it is non-empty and contains the terminal sentinel `("plan", "step1-log")`.
- If all attempts are incomplete, fail with a distinct diagnostic such as `cli _DESIGN_LIFECYCLE_STDOUT_KEYS block extraction incomplete after 3 attempts`.
- Keep the existing `stdout_keys_block` variable name so all four reuse sites keep reading the same validated block.
- Keep each per-verb `missing design <verb>` assertion unchanged. A complete block that truly lacks an entry must still fail with the existing verdict.

## Files to modify/create

### UPDATED: scripts/test-design-structure.sh

Add helper functions near the existing `contains` helpers or immediately before the current capture site:

- `extract_stdout_keys_block`
  - Runs awk against `$CLI_PY`.
  - Starts after `^_DESIGN_LIFECYCLE_STDOUT_KEYS:`.
  - Stops and exits when `$0 == "})"`.
  - Prints only body lines.
- `load_stdout_keys_block`
  - Initializes or updates global `stdout_keys_block`.
  - Loops `attempt=1` to `3`.
  - Uses `if stdout_keys_block="$(extract_stdout_keys_block)"; then ... else stdout_keys_block='' fi` so `set -e` does not abort before retry on an awk failure.
  - Accepts only a non-empty block containing `("plan", "step1-log")`.
  - Calls `fail` with the distinct incomplete-block message after all attempts fail.

Then replace the old direct assignment with:

- `stdout_keys_block=''`
- `load_stdout_keys_block`

Do not change the four grep reuse sites unless needed for shellcheck. They should now operate on a verified complete block.

## Edge cases

- Empty command substitution: retry, then distinct incomplete-block failure.
- Capture truncated before `("plan", "step1-log")`: retry, then distinct incomplete-block failure.
- Awk exits non-zero or is killed: retry instead of exiting early under `set -e`.
- Genuine absent verb in a complete block: preserve the existing `cli _DESIGN_LIFECYCLE_STDOUT_KEYS missing design <verb>` failure.
- Future changes to the frozenset's last entry: update the terminal sentinel in the helper in the same change.
- Future formatting change to the frozenset close line: update the exact `})` close matcher, or use a reviewed equivalent.

## Out-of-scope siblings

Do not refactor unrelated captured-once blocks in this change.

Name these in the PR description as intentionally out of scope:

- `shared_postplan_body`: same broad pattern, but lower exposure, not observed to flake, and lacks a clean terminal sentinel.
- `shared_postplan_body` inverse absence assertions: truncation can cause a spurious pass, not the reported false-negative.
- `_run_finalize_body` inverse absence assertion: truncation can cause a spurious pass, not the reported false-negative.
- Line-index captures near the top of the harness: single-value extraction, not the same reused block class.

## Failure modes

- If the helper sentinel is stale, the harness fails early with the incomplete-block diagnostic.
- If the awk close matcher is wrong, the sentinel check may still pass while over-capturing. Review the extracted range during implementation.
- If retry logic is written as a plain assignment under `set -e`, a killed awk can abort before retry. Use an `if assignment; then` shape.

## Testing strategy

Run changed-file checks only:

- `bash -n scripts/test-design-structure.sh`
- `bash scripts/test-design-structure.sh`
- `make test-design-structure`
- If available locally, run shellcheck on `scripts/test-design-structure.sh`.

Optional local smoke test: in a throwaway copy or temporary local edit, make the terminal sentinel impossible and confirm the harness reports `block extraction incomplete`, not `missing design <verb>`. Revert before commit.

## Acceptance

Run changed-file checks only:

- `bash -n scripts/test-design-structure.sh`
- `bash scripts/test-design-structure.sh`
- `make test-design-structure`
- If available locally, run shellcheck on `scripts/test-design-structure.sh`.

Optional local smoke test: in a throwaway copy or temporary local edit, make the terminal sentinel impossible and confirm the harness reports `block extraction incomplete`, not `missing design <verb>`. Revert before commit.

review_status: complete
rounds_completed: 1
difficulty: MODERATE
diff_added: 30
diff_deleted: 1
mechanical_churn: false
diff_lines: 31
