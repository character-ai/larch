## Proposed Design Outline

### Goals
- Create `rebase.py`: rebase the feature branch onto `origin/main`, deterministically auto-resolve trivial/bump-only/CHANGELOG conflicts, drop the stale bump (+ companion CHANGELOG) commit before replay, run an in-process fixer waterfall for non-trivial conflicts, re-classify/re-bump, force-push-with-lease, and cap attempts.
- Reuse the Phase 1/2 foundation through an injected `proc.Runner`; return a typed `Outcome`/`StepResult` (raise `NeedsUserInput`/`Stalled` on exhaustion).
- Ship colocated `test_rebase.py` deterministic-path parity tests with a stub runner and a stub agent waterfall.

### Non-goals
- No top-level `ship.py` driver wiring; zero change to the live `/implement` path (Phase 7 owns cutover).
- No persisted state machine or `REBASE_COUNT` counter; recover from git/gh ground truth.
- No incidental `/implement` orchestration (`record_failure` issue-logging, larch-logs pre-flush, resume flags).

### Approach sketch
- One entry point, e.g. `rebase_and_rebump(runner, launch_fn, *, base_remote, base_ref) -> StepResult`, driving fetch → drop-bump → rebase → resolve → re-bump → force-push.
- Deterministic auto-resolve: CHANGELOG/bump-only via `changelog.auto_resolve`; drop stale bump + `Update CHANGELOG` commits via `version_bump.drop_bump_commit` + `bump_worktree.drop_replay_commit`.
- Non-trivial conflict → build fixer prompt → `agents.run_waterfall` (Cursor→Codex→Claude, injectable `launch_fn`) → apply resolution → `git rebase --continue`, in a capped fixer loop.
- Re-classify/re-bump via `version_bump.classify_bump`/`apply_bump`; `git.force_push_with_lease`; attempt cap derived from git ground truth → `Stalled`/`NeedsUserInput`.

### Surfaces in scope
- New: `python/rebase.py`, `python/test_rebase.py`.
- Updated: `python/config.py` (rebase-attempt + fixer-loop cap constants), `python/README.md` (Phase 3 line).
- Read-only ports: `scripts/rebase-push.sh`, `run_rebase_rebump` in `scripts/ship-pr.sh`, `scripts/auto-resolve-changelog.sh`, `skills/implement/references/conflict-resolution.md`.

### Open questions
- None. The three scope forks (fixer fidelity, orchestration boundary, parity form) were resolved in Round 1.
