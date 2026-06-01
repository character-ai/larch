## Decision 1: Scope — which of the three bundled gaps this design covers
- **Question**: #3317 bundles 3 parity gaps with different readiness. Which does this design implement?
- **Resolution**: Cover **gap #2** (`defer_push`/`has_bump` inputs) and **gap #3** (`apply_bump` base reconciliation). **Defer gap #1** (pre-drop `refresh-run-logs` + `larch-logs/` fixup) to the Phase 7 `ship.py` driver.
- **Source**: user

## Decision 2: Gap #1 placement — pre-drop refresh-run-logs + larch-logs/ fixup
- **Question**: Implement gap #1 in `rebase.py` now, or defer to the future `ship.py` driver?
- **Resolution**: **Defer to ship.py driver (Phase 7).** It is driver-owned, depends on the un-ported `refresh-run-logs.sh` + implement-only `STATE_FILE`/`IMPLEMENT_TMPDIR`, and `rebase_and_rebump` has no driver caller yet. **Phase 7 issue #3240 amended** with this decision (comment 4589105404).
- **Source**: user

## Decision 3: Gap #3 approach — version-regression guard base vs apply_bump origin/main
- **Question**: `apply_bump` hardcodes `origin/main` while the rebase guard uses `base_remote`/`base_ref`. Reconcile by threading base, or keep strict bash parity?
- **Resolution**: **Thread `base_remote`/`base_ref` into `apply_bump`** so its fetch + version guard use the same base as the rebase guard. Fixes the latent fork/upstream inconsistency. Note: bash `apply-bump.sh` also hardcodes origin/main, so this is an improvement beyond strict parity — acceptable.
- **Source**: user

## Decision 4: Gap #2 API shape — defer_push / has_bump defaults
- **Question**: What defaults for the new `defer_push` / `has_bump` inputs?
- **Resolution**: `defer_push: bool = False`, `has_bump: bool = True` (keyword-only). Defaults preserve today's behavior; existing direct-call tests stay green. `defer_push=True` skips the force-push; `has_bump=False` skips the classify/apply/changelog block. Mirrors bash defaults (`defer_push=false`, `HAS_BUMP != false`).
- **Source**: user

## Decision 5: Hard constraints — must not break
- **Question**: What existing behavior/invariants must be preserved?
- **Resolution**: (a) Runtime stays **stdlib-only** (Python ≥ 3.12). (b) Existing `python/test_rebase.py` + `python/test_version_bump.py` must stay green — `apply_bump` keeps its current single caller (`rebase.py:598`), and base params default to `origin`/`main`. (c) Per #3132 quality bar, add **bash-parity / unit tests** for the new `defer_push` / `has_bump` branches and the base-threaded `apply_bump` guard. (d) `apply_bump`'s injectable `proc.run` seam and redaction stay intact.
- **Source**: codebase

## Decision 6: classify_bump origin/main hardcode (related, out of scope)
- **Question**: `classify_bump` also hardcodes `origin/main` — fold it into gap #3?
- **Resolution**: **No.** Issue #3311 names only `apply_bump` (~566-578). `classify_bump`'s origin/main usage is the diff/classification base (bash `classify-bump.sh` uses origin/main too) and is a separate concern. Keep gap #3 scoped to `apply_bump`; note `classify_bump` as a future observation, do not expand scope on a SIMPLE tier.
- **Source**: codebase

Decisions resolved: 6.
