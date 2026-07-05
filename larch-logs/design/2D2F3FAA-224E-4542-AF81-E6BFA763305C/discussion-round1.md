## Decision 1: Capture fix approach

- **Question**: Which approach to use for eliminating the 100-line truncation in `run_logs_failed`?
- **Resolution**: Option (a) — return the full `--log-failed` output without truncating. Drop the `tail_lines`-based truncation logic; keep the pointer line but update its wording.
- **Source**: user

## Decision 2: Procedure wording for step 6

- **Question**: Should step 6 of `ship-pr-ci-fix.md` require fixing all revealed failing jobs before push, or keep it as a strong recommendation?
- **Resolution**: Hard rule — reword step 6 to explicitly require enumerating every failing job/check and fixing all of them before running checks, staging, committing, and pushing. The 30-attempt counter remains the safety net for genuinely flaky/re-surfacing failures.
- **Source**: user
