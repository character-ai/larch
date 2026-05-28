# test-step0b-router-flag-recovery.sh

**Purpose**: regression harness for the `SKILL.md` Step 0b router-flag recovery guard
and jq-merge. Exercises both true-branch merge (cases 1-4) and false-branch no-op
(case 5).

**Primary**: `scripts/write-run-params.sh` + `skills/design/SKILL.md` Step 0b.

**Edit-in-sync**: `merge_run_params()` and `recovery_merge_if_needed()` must match
`skills/design/SKILL.md` Step 0b. Drift is caught by the full jq-filter pin in
`scripts/test-design-structure.sh` (plus existing per-arm pins at lines 396 and 506).

**Run**: `bash scripts/test-step0b-router-flag-recovery.sh` or `make test-step0b-router-flag-recovery`.

**Coverage gap closed**: #3008 — `--manual-only` argv after successful
`write-run-params.sh` (case 1) and the outer guard's false-branch no-op (case 5).
