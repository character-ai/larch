# Design Discussion — Round 1 (Issue #4589)

Scope: defer `larch_quiet_init` until after `session validate-design-tmpdir` in the
embedded `_LEGACY_ASSETS` bash bodies in `python/plan_review.py`, mirroring the
live #3780 wrappers and the SECURITY.md allowlist-before-quiet rule.

## Decision 1: Fix breadth (which embedded scripts get the reorder)
- **Question**: The issue names 5 scripts, but decoding every `_LEGACY_ASSETS` entry found two more that also run `larch_quiet_init` before `validate-design-tmpdir`: `run-step3-review.sh` (LIVE, executed via `plan-review run`; gets quiet-init transitively via `lib-phase-driver.sh`) and `tally-plan-review.sh` (embedded body retained but no longer executed). Which set?
- **Resolution**: ALL 7 quiet-before-validate scripts — `emit-plan.sh`, `finalize-plan.sh`, `dispatch-plan-review-panel.sh`, `plan-review-loop.sh`, `dispatch-plan-voters.sh` (the 5 named) **plus** `run-step3-review.sh` and `tally-plan-review.sh`.
- **Source**: user

## Decision 2: No-validate scripts (persist-retally, record-timing)
- **Question**: `persist-retally-step3-env.sh` and `record-plan-review-round-timing.sh` source lib-quiet and call `larch_quiet_init` but NEVER call `validate-design-tmpdir` (only basic `-d`/`! -L` checks). 'Move quiet after validate' is unsatisfiable without adding a validate call. How to handle?
- **Resolution**: ADD a `session validate-design-tmpdir` call (after arg-parse, before any DESIGN_TMPDIR write) to each, and init quiet immediately after it. Net effect: all 9 embedded scripts that call `larch_quiet_init` validate first.
- **Source**: user

## Hard constraint 1: Source `.sh` files are retired/absent
- **Finding**: All five named source scripts (and the others) are absent from the repo — the gzip+base64 blobs in `_LEGACY_ASSETS` are the ONLY copy, and no regeneration tooling exists. The fix must decode → edit → re-gzip/base64 → replace the blob string literal in `python/plan_review.py`. Native in-process ports remain follow-up scope per `docs/python-migration.md §C3a1`.
- **Source**: codebase

## Hard constraint 2: Preserve the runtime waterfall substitution
- **Finding**: `_decode_legacy_asset` applies post-decode text substitutions for `dispatch-plan-voters.sh` (`_ROOT_VOTER_DISPATCH`) and `dispatch-plan-review-panel.sh` (`_DESIGN_PANEL_DISPATCH`) — replacing retired `dispatch-with-waterfall.sh` references with `agent dispatch-waterfall`. Blob regeneration for those two MUST round-trip via the RAW `_decode_asset` (NOT `legacy_asset_bytes`), edit, re-encode — so the substitution markers (`"$PLUGIN_ROOT/scripts/dispatch-with-waterfall.sh"`, etc.) survive untouched.
- **Source**: codebase

## Hard constraint 3: Keep the `source` lines; move only the `larch_quiet_init` call
- **Finding**: `larch_err` (from lib-quiet) is used in `usage()` and arg-parse error paths that run BEFORE validate. So the `source ".../lib-quiet.sh"` (and `source lib-phase-driver.sh`) lines stay at the top; only the `larch_quiet_init` invocation moves to after the validate call. Blob byte changes must be limited to the quiet-init line move (+ the added validate line for the 2 no-validate scripts) — a decode-diff of old vs new must show ONLY those intended changes.
- **Source**: codebase

## Hard constraint 4: Keep canonical docs in sync (SECURITY.md)
- **Finding**: SECURITY.md (~line 166) documents the `/design` allowlist-before-quiet ordering and names the 3 live #3780 wrappers. Per AGENTS.md ("Update SECURITY.md when security-relevant behavior changes"), extend it to note the embedded `_LEGACY_ASSETS` bodies now follow the same ordering.
- **Source**: codebase

## Out of scope
- Native in-process ports of the retired scripts (C3a1 follow-up).
- Restoring the deleted source `.sh` files / changing `_materialize_legacy_root` to read from disk.
- Adding allowlist validation to scripts that neither source lib-quiet nor call `larch_quiet_init`.
