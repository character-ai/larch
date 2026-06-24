## Goal
Implement issue #5312: [IMPLEMENTING] [BUG] review-and-fix coder commit fails when process CWD is not the git repository root.

## Implementation Plan
## Summary

`review-and-fix step5` (`_stage_and_commit_round` in `python/review_and_fix.py`) runs `git add --pathspec-from-file` with the caller's inherited working directory rather than the repository root. When the process CWD is a subdirectory (e.g., `python/`), git cannot find repo-relative paths like `python/implement_dispatch.py` (resolves to `python/python/implement_dispatch.py`, which does not exist). The commit fails silently with `CODER_STATUS=failed`, which surfaces as `STEP5_REVIEW_STATUS=stall STALL_REASON=coder-failed` after retries exhaust without a clear explanation.

## Original report

During an `/implement --emergency 5307` run, Step 5 code review stalled with `STALL_REASON=coder-failed` on every attempt. The Cursor coder completed successfully (exit code 0, output "APPLIED: FINDING_4, APPLIED: FINDING_5"), but the subsequent `_stage_and_commit_round` commit step failed with:

```
warning: could not open directory 'python/python/': No such file or directory
fatal: pathspec 'python/implement_dispatch.py' did not match any files
warning: could not open directory 'python/python/': No such file or directory
fatal: pathspec 'python/complexity-baseline.json' did not match any files
```

The `warning: could not open directory 'python/python/'` pattern confirms git was run from the `python/` subdirectory with repo-root-relative pathspecs.

## Reproduction scenario

1. Run a Bash command that changes CWD to a subdirectory (e.g., `cd python && python3 cli.py lint complexity-baseline --write`) during an `/implement` session. The Bash tool persists CWD between calls.
2. Proceed to Step 5 code review via `bash "$IMPLEMENT_TMPDIR/larch-run.sh" skills/implement/scripts/step-5-review.sh`.
3. The review panel runs and finds accepted findings.
4. The coder (Cursor or Codex) applies the findings successfully.
5. `_stage_and_commit_round` calls `_run([sys.executable, str(_PY_CLI), "git", "commit", "--only", "--pathspec-from-file", ...])` with the inherited (wrong) CWD.
6. `git add --pathspec-from-file` fails because repo-relative paths like `python/implement_dispatch.py` do not exist relative to `python/`.
7. `RoundCommitResult` has no SHA → `_cleanup_failed_coder_attempt` → `coder-failed` stall.

## Expected behavior

`_stage_and_commit_round` and `_commit_fixes_stage_all` should be CWD-agnostic. Git operations that use repo-relative pathspecs should either:
- Explicitly pass `cwd=<repo-root>` to `_run`, or
- Validate that the pathspecs are resolvable relative to the current CWD before running.

## Observed behavior

- `coder-cursor.log`: `APPLIED: FINDING_4`, `APPLIED: FINDING_5` (coder succeeded)
- `coder-commit.log`: two `fatal: pathspec ... did not match any files` errors (git failed)
- `coder.env`: `CODER_STATUS=failed`
- `review-and-fix.env`: `REVIEW_AND_FIX_STATUS=coder-failed`
- `step-5-review.sh` output: `STEP5_REVIEW_STATUS=stall STALL_REASON=coder-failed` on all retries

## Root cause analysis

`review_and_fix.py` defines `_run` as `proc.run(argv, cwd=str(cwd) if cwd else None, ...)`. All calls in `_stage_and_commit_round` and `_commit_fixes_stage_all` pass `cwd=None`, inheriting the caller's CWD.

`larch-run.sh` uses `exec python3 "$CLAUDE_PLUGIN_ROOT/$script"` which does not `cd` to the repo root before execution. If the invoking shell has a non-root CWD (e.g., `python/`), all scripts launched through `larch-run.sh` inherit that CWD. The git commit uses repo-root-relative pathspecs (e.g., `python/complexity-baseline.json`), which fail when resolved against a subdirectory CWD.

The underlying fragility: `review_and_fix.py` assumes it will always be called from the repo root. This assumption is not mechanically enforced, and the failure mode (wrong-CWD git pathspec resolution) is non-obvious — the error message does not mention CWD.

## Evidence

- `coder-commit.log` in `$IMPLEMENT_TMPDIR/round-1/`: `warning: could not open directory 'python/python/'` and two `fatal: pathspec ... did not match any files` errors for both `python/implement_dispatch.py` and `python/complexity-baseline.json`.
- `coder-cursor.log` in `$IMPLEMENT_TMPDIR/round-1/`: `APPLIED: FINDING_4`, `APPLIED: FINDING_5` — confirms coder succeeded before commit.
- `coder.env`: `CODER_STATUS=failed`, `CODER_TOOL=cursor`.
- `review-and-fix.env`: `REVIEW_AND_FIX_STATUS=coder-failed`, `REVIEW_CORE_STATUS=fix-required`, `FIX_COUNT=2`.
- `coder-stage-paths.txt` in `$IMPLEMENT_TMPDIR/round-1/`: `python/complexity-baseline.json` (repo-relative path written by `_collect_round_stage_paths`).
- Bash tool CWD set to `python/` by a prior `cd python && ...` command — confirmed by `pwd` output.

## Affected files

- `python/review_and_fix.py` — `_stage_and_commit_round` (line ~2113) and `_commit_fixes_stage_all` (line ~298): both call `_run([sys.executable, str(_PY_CLI), "git", "commit", ...])` with no explicit `cwd`.
- `skills/implement/scripts/step-5-review.sh` — entry point launched via `larch-run.sh`; does not enforce CWD=repo-root before delegating to Python.

## Suggested fix(es)

**Option A (preferred)**: Detect and pin the repo root at `review_and_fix.py` module load time (`_REPO_ROOT = subprocess.check_output(["git", "rev-parse", "--show-toplevel"]).decode().strip()`) and pass `cwd=_REPO_ROOT` to all git invocations in `_stage_and_commit_round` and `_commit_fixes_stage_all`.

**Option B**: Add a CWD guard at the top of `review-and-fix step5` (or in `step-5-review.sh`) that runs `git rev-parse --show-toplevel` and `cd`s to the result before delegating to Python.

**Option C**: Add a pre-flight assertion in `_stage_and_commit_round` that the stage-file pathspecs are resolvable from the current CWD, and emit a clear error (mentioning CWD) rather than a generic `coder-failed` stall when they are not.

## Open questions

- Should `larch-run.sh` always `cd` to `$REPO_ROOT` (resolved from `git rev-parse --show-toplevel`) before `exec`-ing scripts, as a universal guard? This would fix the issue globally but may affect scripts that intentionally run in a subdirectory.
- Is there a `make lint` check that could detect `_run` calls in `review_and_fix.py` that are missing a `cwd` arg and touch git operations?

## Test plan
(no test plan section in plan-file)
