## Decision 1: Conflict-fixer fidelity
- **Question**: How much of the real fixer should Phase 3 build, given acceptance only requires a stub agent?
- **Resolution**: Full in-process fixer — construct the per-conflict fixer prompt, invoke `agents.run_waterfall` (Cursor→Codex→Claude via an injectable `launch_fn`), apply the agent's resolution, `git rebase --continue`, loop with a cap. Tests inject a stub `launch_fn` (no real cursor/codex/claude). Highest fidelity to `conflict-resolution.md`.
- **Source**: user

## Decision 2: /implement orchestration boundary
- **Question**: How much of run_rebase_rebump's incidental orchestration (persisted REBASE_COUNT, record_failure issue-logging, larch-logs pre-flush/fixup, resume flags) belongs in rebase.py?
- **Resolution**: Pure component only. Derive the attempt-cap from git ground truth (no persisted counter — honors locked decision #1). Return a typed `Outcome`/`StepResult`; raise `NeedsUserInput`/`Stalled` on exhaustion. Leave issue-logging, larch-logs fixup, and resume-flag handling to the future `ship.py` driver / later phases.
- **Source**: user

## Decision 3: Parity test form
- **Question**: What "bash-parity per component" form is expected when run_rebase_rebump is not standalone-invocable?
- **Resolution**: Deterministic-path parity via colocated `test_rebase.py` unit tests with a stub `proc` runner + golden fixtures for the portable deterministic paths (drop-bump/drop-changelog replay, force-push-with-lease, auto-resolve dispatch). No twin-repo harness against the embedded `run_rebase_rebump`.
- **Source**: user

## Decision 4: Return contract (must not break)
- **Question**: What is the module's success/failure contract?
- **Resolution**: Reuse `outcomes.Outcome` (OK / NEEDS_USER_INPUT / STALLED / TRANSIENT) + `outcomes.StepResult`, and `errors.NeedsUserInput` / `errors.Stalled`. The component does not exit the process or print user-facing escalation — it returns/raises typed results for the driver to map.
- **Source**: codebase

## Decision 5: Foundation reuse (in-scope, do not re-implement)
- **Question**: Which existing Phase 1/2 surfaces must rebase.py consume rather than re-implement?
- **Resolution**: `changelog.auto_resolve` (CHANGELOG conflict auto-resolve), `version_bump.classify_bump` / `apply_bump` / `drop_bump_commit`, `bump_worktree.drop_replay_commit` / `find_subject_commit_depth`, `git.rebase` / `rebase_onto` / `force_push_with_lease` / `reset` / `status_porcelain` / `fetch` / `merge_base`, `agents.run_waterfall` / `launch_tier` / `build_launch_argv` / `effective_failure_class`. `proc.Runner` is injected for all git/gh/agent shell-outs.
- **Source**: codebase

## Decision 6: New config constants
- **Question**: What new tunables does rebase.py need?
- **Resolution**: Add a rebase-attempt cap constant in `config.py` (bash `_max_rebases=20`) and a fixer-loop iteration cap. Reuse existing `FIXER_TIER_ORDER`, `WATERFALL_MAX_TIERS`, `DROP_BUMP_MAX_DEPTH`, `DROP_CHANGELOG_MAX_DEPTH`. No new runtime dependencies (stdlib-only, Python ≥ 3.12).
- **Source**: codebase

## Decision 7: Strangler-fig boundary (non-goal)
- **Question**: Does Phase 3 wire rebase.py into the live /implement path or a top-level driver?
- **Resolution**: No. `ship.py` (the linear driver) is a later phase. Phase 3 ships `rebase.py` + `test_rebase.py` only; zero change to the live `/implement` path (locked decision #2). Dev/CI-only until the Phase 7 `LARCH_SHIP_PR_IMPL=python` cutover.
- **Source**: codebase + issue
