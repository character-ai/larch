## Proposed Design Outline

### Goals
- Address the 5 in-scope OOS items (A, B, C, E, F) from #3032 in a single combined PR.
- Add telemetry attribution for the `/implement` Step 0 tracking phase (Item B).
- Eliminate silent-zero cost reporting when `token-report.json` is corrupt/all-zeros (Item F).

### Non-goals
- Item D (deferred until Phase 4 / coder waterfall — Round 1 Decision 1).
- Any behavioral change to `phase_tracking` / `phase_infra` KV outputs, sentinels, or breadcrumb names.
- Refactoring the cost-rendering pipeline; only add a corrupt-detection warning.
- New harness cases beyond the two documented bail paths in Item C.

### Approach sketch
- Insert `token-ledger.sh mark` + `timing-ledger.sh mark "Step 0 — tracking issue"` at the top of `phase_tracking()` in `scripts/implement-bootstrap.sh` (mirroring the `phase_infra` pattern at lines 450-451).
- Add a corrupt-zeros detector in the cost-rendering path: when `token-report.json` exists but `.claude.totals`, `.codex.totals`, `.cursor.totals` all sum to 0, emit `**⚠ token-report.json appears corrupt; reporting $0.00**` and continue.
- Rewrite the stale "future phases will add" prose in `scripts/implement-bootstrap.md` to enumerate the tracking breadcrumbs Phase 2 actually emits today.
- Add 2 new harness cases to `skills/implement/scripts/test-implement-bootstrap.sh`: (1) `get-issue-state.sh` returns a non-OPEN/non-CLOSED state; (2) Branch-1 resume invoked without `--issue-number`.
- Update `docs/linting.md` `make test-implement-bootstrap` row description from "Step 0 calls #1–#5" to "Step 0 calls #1–#9" with the post-Phase-2 case list.

### Surfaces in scope
- `scripts/implement-bootstrap.sh` (phase_tracking ledger marks — Item B)
- `scripts/implement-bootstrap.md` (breadcrumb prose freshness — Item A)
- `skills/implement/scripts/test-implement-bootstrap.sh` (+2 cases — Item C)
- `skills/implement/scripts/test-implement-bootstrap.md` (sibling test doc sync — Item C)
- `docs/linting.md` (`make test-implement-bootstrap` row — Item E)
- `scripts/render-run-summary.sh` and/or `skills/implement/scripts/write-final-report.sh` (corrupt-zero warning — Item F)

### Open questions
- Item F warning placement: emit from `render-run-summary.sh` (single emission point covering both consumers) vs. `write-final-report.sh` (closer to the per-run report). Step 2a sketches + Step 2b plan will resolve.
