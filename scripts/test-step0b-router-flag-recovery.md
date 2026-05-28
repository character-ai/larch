# test-step0b-router-flag-recovery.sh

**Purpose**: regression harness for the `SKILL.md` Step 0b router-flag recovery guard
and jq-merge. Exercises both true-branch merge (cases 1-4), false-branch no-op
(case 5), writer-failure abort before recovery (case 7), and the success-path
positive control that recovery completes after a successful write (case 7b).

**Primary**: `scripts/write-run-params.sh` + `skills/design/SKILL.md` Step 0b.

**Edit-in-sync**: `merge_run_params()` and `recovery_merge_if_needed()` must match
`skills/design/SKILL.md` Step 0b. `write_then_recover()` composes (does not modify)
`recovery_merge_if_needed()`, so the existing edit-in-sync jq-filter pins remain
unaffected. Drift is caught by the full jq-filter pin in `scripts/test-design-structure.sh`
(plus the per-arm jq pins at lines 404 and 514, and the outer guard pin at line 401).

**Run**: `bash scripts/test-step0b-router-flag-recovery.sh` or `make test-step0b-router-flag-recovery`.

**Coverage gap closed**: #3008 — `--manual-only` argv after successful
`write-run-params.sh` (case 1), the outer guard's false-branch no-op (case 5),
and the missing-`run-params.json` degraded warning path (case 6). #3161 — a hard
`write-run-params.sh` failure aborts before the recovery merge runs (case 7); case 7b
proves the composed `write_then_recover()` path still reaches and completes recovery
on success.
