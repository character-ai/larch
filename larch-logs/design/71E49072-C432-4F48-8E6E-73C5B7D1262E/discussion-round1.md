## Decision 1: Fix scope — design ranking parity only
- **Question**: Issue #4959 has an empty body; the title is "Live-run discovery uses inconsistent and incomplete liveness signals." How far should the fix go (ranking parity / + cwd-source parity / + idle-heartbeat liveness)?
- **Resolution**: Design ranking parity ONLY. Apply the #4954 fix to the design discovery path: `_design_candidate` in `python/progress_report.py` must rank by `_run_activity_mtime(tmpdir / "timing-ledger.tsv", pointer)` (timing-ledger activity, pointer-mtime fallback) instead of the frozen `_path_mtime(pointer)`, so the design and implement discovery paths rank concurrent same-repo runs identically.
- **Source**: user (Step 1c AskUserQuestion)

## Decision 2: Also align the /cleanup design reaper
- **Question**: Should `cleanup_skill.py`'s stale-pointer reaper (a third liveness definition) also be aligned with discovery's notion of "live"?
- **Resolution**: Yes. Align `cleanup_skill.py`'s design pointer reaper so its staleness definition matches discovery (reap when the resolved DESIGN_TMPDIR directory is gone), mirroring the existing implement reaper that reaps when IMPLEMENT_TMPDIR is gone. Preserve the existing dangling-symlink reaping behavior as a subset.
- **Source**: user (Step 1c AskUserQuestion)

## Decision 3: Out-of-scope (explicit refusals)
- **Question**: Are cwd-source parity and a positive idle/heartbeat liveness check in scope?
- **Resolution**: NO to both.
  - cwd-source parity (design reads `.larch-keepalive`→`CLONE_PATH`; implement reads pointer→`REPO_CWD`) is explicitly OUT of scope.
  - A positive idle/heartbeat staleness check (detecting crashed-but-tmpdir-present runs) is explicitly OUT of scope (the original progress-hook design deferred this to future work).
- **Source**: user (Step 1c AskUserQuestion)

## Decision 4: Hard constraints (must not break)
- **Question**: What existing behavior must be preserved?
- **Resolution**:
  - The just-merged #4954 implement-side behavior (`_implement_candidate` ranking) must remain unchanged.
  - Backward compatibility: when a design run has no timing-ledger activity yet (very early, before the first ledger row), ranking must fall back to the pointer mtime (the existing `_run_activity_mtime` fallback), preserving today's design behavior at that stage.
  - The existing dangling-symlink reaping in `/cleanup` must continue to work.
  - This is an OOS cleanup follow-up to #4954: bias to the smallest change that unifies the signals.
- **Source**: codebase + user
