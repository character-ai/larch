# test-design-step2b-drafter.sh

Offline harness for `design-step2b-drafter.sh` Codex token sidecar handling.

It stubs `launch-codex-drafter.sh` under a temporary plugin root, seeds a stale
`step2b-drafter-status.txt.token-record`, and asserts no stale
`codex_plan_draft` row reaches either `$DESIGN_TMPDIR/token-report.ndjson` or
the active design token ledger. It then simulates a fresh successful Codex
drafter sidecar and asserts exactly one `codex_plan_draft` row reaches both
ledgers with `MODEL=` preserved.

Edit in sync with `design-step2b-drafter.sh`, `design-step2b-drafter.md`, and
`scripts/launch-codex-drafter.sh`. Run through `make test-design-step2b-drafter`
and relevant-check mappings for Step 2b/drafter files.
