# scripts/ci-rerun-failed.sh — contract

`scripts/ci-rerun-failed.sh` wraps `gh run rerun --failed` for the `/implement` Step 10 and Step 12c transient-CI-retry paths. Inputs are `--run-id` and `--repo`; outputs are `RERUN_SUBMITTED=true|false` plus an `ERROR=<msg>` line on failure. The script always exits 0 — callers branch on `RERUN_SUBMITTED`. Timing policy (sleeps before / between retries) belongs to the orchestrator, not to this script — see `skills/implement/SKILL.md` Step 10 and Step 12c for the canonical retry caps and sleep durations.

When `gh run rerun` fails with "This workflow is already running", `RERUN_SUBMITTED=true` is emitted with an empty `ERROR` — the run is already in progress so no rerun is needed. All other non-zero exits produce `RERUN_SUBMITTED=false` with the error text.

Regression harness: `scripts/test-ci-rerun-failed.sh`.
