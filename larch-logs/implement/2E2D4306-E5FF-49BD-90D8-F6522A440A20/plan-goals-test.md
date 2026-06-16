## Goal
Implement issue #4509: [IMPLEMENTING] dirty-tree checkpoint in plan-review-loop: wrong cwd causes false-positive WARN.

## Implementation Plan
**Root cause**: `_run_legacy` in `python/plan_review.py` (line 1124) runs embedded scripts with `cwd=_REPO_ROOT` where `_REPO_ROOT = Path(__file__).resolve().parents[1]` — the larch plugin cache directory (e.g. `~/.claude/plugins/cache/larch-local/larch/50.1.7`). This is NOT a git repository. When `plan-review-loop.sh` (the embedded script) calls `python3 "$PLUGIN_ROOT/python/cli.py" dirty-tree checkpoint` without a `--cwd` argument, `checkpoint()` in `dirty_tree.py` inherits the shell's cwd (the larch plugin cache) and runs `git status --porcelain` there. Git exits 128 (`fatal: not a git repository`), which `checkpoint()` maps to `STATUS=unknown REASON=git-status-failed`. The loop condition `grep -qE '^STATUS=(dirty|unknown)$'` then matches, emitting the false-positive WARN `plan-review-collection: dirty tree detected`.

**Observed symptoms**:
- `$DESIGN_TMPDIR/dirty-tree-detected.env` contains `STATUS=unknown MODE=checkpoint REASON=git-status-failed` after plan-review-collection
- `WARN=plan-review-collection: dirty tree detected` appears in the design-step3-review.sh output
- All 12 per-reviewer `.dirty-tree` sidecars show `STATUS=clean` (no actual mutations)
- `git status --short` in the consumer repo is clean

**Evidence path**: `plan_review.py:1124` (`cwd=str(_REPO_ROOT)`), `dirty_tree.py:79` (`_run_bytes(["git", "status", "--porcelain"], cwd=cwd)`), embedded `plan-review-loop.sh` (gzip-embedded in `plan_review.py`, ~line 1288): `if grep -qE '^STATUS=(dirty|unknown)$' <<< "$_dirty_out"`.

**Suggested fix options**:
1. **Smallest**: Change the condition in the embedded `plan-review-loop.sh` from `^STATUS=(dirty|unknown)$` to `^STATUS=dirty$` to avoid treating git infrastructure failures as dirty-tree evidence. Or add a `REASON` check to exclude `REASON=git-status-failed` from triggering the WARN. This prevents the false positive but the collection-phase dirty-tree check would silently no-op if git genuinely fails.
2. **Correct**: Add `--cwd` support to `dirty-tree checkpoint` (`checkpoint_main` in `dirty_tree.py`), then pass `--cwd "$LARCH_CONSUMER_REPO"` from `plan-review-loop.sh`. The consumer repo path needs to be threaded in (possibly via an env var from the design session env, since `design-step3-review.sh` knows the consumer working directory). `_run_legacy` already sets `LARCH_REAL_PLUGIN_ROOT` in the child env; a parallel `LARCH_CONSUMER_REPO` env var set by the caller before invoking `cli.py plan-review run` would suffice.
3. **Structural**: Run `plan-review-loop.sh` with `cwd=consumer_repo` rather than `cwd=_REPO_ROOT`, but that requires changes to `_run_legacy`'s caller contract.

**Reproduction**: any `/design` run on a repo where the larch plugin is installed from the marketplace cache (not a git worktree) will reproduce this false positive. The consumer repo is clean; the plugin cache is not a git repo.

## Test plan
(no test plan section in plan-file)
