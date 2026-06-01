# scripts/test-step-telemetry-mark.sh — contract

Offline unit harness for `scripts/step-telemetry-mark.sh`. Full helper contract:
`scripts/step-telemetry-mark.md`.

Asserts `[ -x "$HELPER" ]` and invokes the helper **by direct path** (not `bash "$HELPER"`) on the happy path so a missing executable bit is caught before SKILL.md call sites silently drop marks via `|| true`.

Covers: happy path (both ledger marks), bad `--implement-tmpdir`, omitted `--implement-tmpdir`, and missing `--label` (all exit 0).

Wired into `make test-step-telemetry-mark`.
