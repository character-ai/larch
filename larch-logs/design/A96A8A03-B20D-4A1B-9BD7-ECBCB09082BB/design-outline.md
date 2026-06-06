## Proposed Design Outline

### Goals
- Close the implement-side timing-attribution A1-scanner gap: have `scripts/test-implement-structure.sh` cover `record-implement-review-round-timing.sh` and its `record-round` subcommand, so a dropped/misattributed `LARCH_TIMING_SKILL=implement` pin fails CI.
- Make the implement deferred round-timing writer overwrite stale/partial rows via full-tuple fingerprinting (round+start+end), matching the design-helper variant.
- Pin the `/implement` lint-fix Codex dispatch to `LARCH_TIMING_SKILL=implement` so its vendor row is not misattributed under a polluted shell, locked in by a regression assertion.

### Non-goals
- No blanket `LARCH_TIMING_SKILL=implement` pin on the generic `scripts/launch-codex-exec.sh` (it also serves design/review/research).
- No design-side mirror or net-new design A1 scanner (`test-design-structure.sh` has no equivalent today).
- No change to the `timing-ledger.tsv` row schema or `timing-ledger.sh` subcommand contracts.

### Approach sketch
- Extend the A1 scanner in `scripts/test-implement-structure.sh`: add the helper to the enumerated emitter set, teach `is_timing_call` the `record-round` subcommand, and accept an export-or-same-line pin for that helper without weakening strict same-line enforcement for the existing emitters.
- Align the idempotency pre-check in `record-implement-review-round-timing.sh` (lines 99-105) to full-tuple (round+start+end) fingerprinting so a stale partial row is overwritten, not silently reused.
- Add an implement-session timing guard at the lint-fix Codex dispatch site in `scripts/lint-fix-loop.sh` (`run_codex`), plus a pinning assertion in the scanner.
- Update sibling `.md` contracts and the helper's regression harness (`test-record-implement-review-round-timing.sh`) for the new behavior.

### Surfaces in scope
- `scripts/test-implement-structure.sh` (A1 scanner + Part B pin assertion)
- `skills/review-and-fix/scripts/record-implement-review-round-timing.sh`
- `scripts/lint-fix-loop.sh` (`run_codex` dispatch site)
- Sibling `.md` docs + `skills/review-and-fix/scripts/test-record-implement-review-round-timing.sh`

### Open questions
- None. Scope resolved in Round 1 (full issue scope, implement-only).
