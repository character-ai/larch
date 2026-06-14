# test-design-step2b-drafter.sh

Offline harness for `design-step2b-drafter.sh`.

It covers folded prelude setup for every case: `approach-synthesis.txt`, `contested-decisions.md`, empty `dialectic-resolutions.md`, `.completed` repair, and fake plugin scaffolding. Exact sentinel helper behavior is pinned, including multi-line, trailing-whitespace, and extra-blank-line rejection. The harness asserts the drafter wrapper must not source `design-step2b-prelude.sh`.

It covers delegated postplan expectations, pinned launcher transport argv, machine-safe preview output, incomplete internal-postplan output, fatal postplan rc handling, dirty-tree recovery, and drafter fallback. rc 11 coverage uses the real `design-step2b-postplan.sh` wrapper with fake lower-level dependencies, not only a stub.

Token sidecar scenarios also satisfy folded-prelude artifacts and fake postplan scaffolding. They assert stale sidecars are ignored, fresh Codex sidecars are ingested exactly once, and stale parent token ledger settings do not leak into the active design ledger.

Edit in sync with `design-step2b-drafter.sh`, `design-step2b-drafter.md`, `design-step2b-postplan.sh`, and `scripts/launch-codex-drafter.sh`. Run through `make test-design-step2b-drafter` and relevant-check mappings for Step 2b/drafter files.
