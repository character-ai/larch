## Scope decision from #3317 `/design` (Round 1, 2026-05-31)

The pre-drop **`refresh-run-logs` + `larch-logs/` fixup** is **deferred to this Phase 7 driver** — it will **not** land in `python/rebase.py`.

**What this is.** Bash `run_rebase_rebump` (`scripts/ship-pr.sh` ~3196–3236) flushes pending run-log writes (`refresh-run-logs.sh`) and commits tracked `larch-logs/` leftovers **before** `drop-bump-commit`, so the drop guard cannot stall on a dirty tree (issues #2952 Bug B, #3209). Source OOS finding: gap #1 of #3317 (was #3309), Cursor-Edge.

**Why it belongs here, not in `rebase.py`.**
- It is **driver-owned**: it manipulates implement-run state, not rebase mechanics.
- It depends on infrastructure **not yet ported** — there is no Python `refresh-run-logs` equivalent, and it reads implement-only `STATE_FILE` / `IMPLEMENT_TMPDIR`.
- `python/rebase.py:rebase_and_rebump` has **no driver caller** until this phase, so `rebase.py` stays driver-agnostic.

**Phase 7 action item.** In `ship.py`, run the pre-drop fixup (flush run-logs, then commit tracked `larch-logs/` leftovers) **before** calling `rebase.rebase_and_rebump`. This aligns with the driver's existing `Flush Logs → Rebase` flow. Without it, Python `version_bump.drop_bump_commit` can return `dropped=false` / raise `Stalled` on a dirty tracked `larch-logs/` tree, matching the bash failure class #3209 guards against.

The other two #3317 gaps (gap #2 `defer_push`/`has_bump` inputs, gap #3 `apply_bump` base reconciliation) are landing on `python/rebase.py` / `python/version_bump.py` in the #3317 design.
