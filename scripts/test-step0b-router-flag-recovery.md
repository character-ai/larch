# test-step0b-router-flag-recovery.sh

**Purpose**: regression harness for Step 0b router-flag recovery and jq-merge. Exercises fresh `design-init-runparams.sh` true-branch merge (cases 1-4), false-branch no-op (case 5), the missing-file degraded warning path (case 6), writer-failure abort before recovery (case 7), the success-path positive control that recovery completes after a successful write (case 7b), and `design-route.sh` driver-owned route merge for already-planned flows (case 12).

**Primary**: `python/cli.py session write-run-params`, `skills/design/scripts/design-init-runparams.sh`, `skills/design/scripts/design-route.sh`, and `skills/design/scripts/design-step0-route.sh` (the SKILL.md route wrapper that forwards argv flags to the driver).

**Edit-in-sync**: `merge_run_params()` and `recovery_merge_if_needed()` must match the fresh-flow merge in `design-init-runparams.sh`; case 12 must match `design-route.sh` route-only `merge_router_flags()` and `design-step0-route.sh` flag-forwarding. `write_then_recover()` composes (does not modify) `recovery_merge_if_needed()`, so the existing edit-in-sync jq-filter pins remain unaffected. Drift is caught by the full jq-filter pins in `scripts/test-design-structure.sh`.

**Run**: `bash scripts/test-step0b-router-flag-recovery.sh` or `make test-step0b-router-flag-recovery`.

**Coverage gap closed**: router flag true-branch recovery after successful
`session write-run-params` (cases 1-4), the outer guard's false-branch no-op (case 5),
and the missing-`run-params.json` degraded warning path (case 6). #3161 — a hard
`session write-run-params` failure aborts before the recovery merge runs (case 7); case 7b
proves the composed `write_then_recover()` path still reaches and completes recovery
on success. Case 12 proves current argv flags are OR-merged by `design-route.sh` for already-planned routing before control returns to prompt-side gates.
