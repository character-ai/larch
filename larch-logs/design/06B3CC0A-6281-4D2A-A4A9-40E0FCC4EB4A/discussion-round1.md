## Decision 1: Test-coverage scope — both Step 5 bash wrappers
- **Question**: The issue names step-5-review.sh's DIFFICULTY_OVERRIDE→--difficulty forwarding gap. step-5-resume.sh has the identical forwarding pattern (same `read_run_flag_key DIFFICULTY_OVERRIDE`, same case-validate, same conditional `--difficulty` append) and the identical missing coverage. Should the fix cover both wrappers?
- **Resolution**: Cover both. Add behavioral coverage for step-5-review.sh AND step-5-resume.sh.
- **Source**: user

## Decision 2: Fix scope is test-only (no production code changes)
- **Question**: Does closing this gap require changing step-5-review.sh / step-5-resume.sh forwarding logic itself?
- **Resolution**: No. Current forwarding logic is correct — grep/read of both scripts confirms `DIFFICULTY_OVERRIDE` is read via `read_run_flag_key`, validated against `""|TRIVIAL|MODERATE|HARD`, and conditionally forwarded as `--difficulty`. The issue describes a coverage gap for a hypothetical future regression ("would not be caught"), not a live bug. Add behavioral tests only; no wrapper script edits.
- **Source**: codebase
