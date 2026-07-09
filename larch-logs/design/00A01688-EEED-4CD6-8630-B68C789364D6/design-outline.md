## Proposed Design Outline

### Goals
- Stop the post-merge proactive transient retry from rebasing + force-pushing the already-merged, closed-PR branch.
- Preserve #6610's intended recovery: the reship still resumes at `postmerge-push-watch` and re-checks main CI health.

### Non-goals
- No change to `Outcome.TRANSIENT` emission, the retry counter, or the transient→reship conversion.
- No change to `_emergency_repair_transient_recovery_result` (manual-recovery path; already bypasses pre-fix rebase).
- No change to open-PR pre-fix rebase behavior (`ci-fix` / normal reship on live PRs).

### Approach sketch
- Add a `PR_CLOSED=true` skip guard at the top of `_ship_pre_fix_rebase_step` in `dispatch_ship.py`.
- Mirror the existing `_ship_pre_fix_phase14_skip_allowed` skip: return `(None, "skip", "continue")`.
- Skip → `ship_pre_fix_rebase_main` writes `.ship-pre-fix-rebase-ok` + emits `NEXT_ACTION=continue`, satisfying the orchestrator proof-guard so the reship relaunch proceeds.
- Reuse `_ship_pre_fix_truthy`; `PR_CLOSED` is already read by `_ship_pre_fix_read_state`.

### Surfaces in scope
- `python/larch/implement/dispatch_ship.py` (guard).
- `python/tests/implement/test_implement_dispatch.py` (regression test).
- `skills/implement/references/ship-pr-exit-matrix.md` (one-line carve-out note; conditional).

### Open questions
- Guard key: `PR_CLOSED=true` (broad, semantically correct — recommended) vs. narrower `PHASE=postmerge-push-watch`. Defer final call to plan review.
