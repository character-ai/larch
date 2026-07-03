## Goal
Implement issue #6199: [IMPLEMENTING] [Bug] /implement terminal: Step 4 commit-route skips new lint-fix edits once the dispatcher has committed, leaving the tree dirty before the 4.r rebase check (contract-failure at 3).

## Implementation Plan
<!-- larch-stall:signature=2645f8c562919820cb2b2790594e3fffda0c0156a4c489c4548fda11831e5d3d -->
## Report metadata
- **Report kind**: `terminal-failure`
- **Failure class**: `contract-failure`
- **Step**: `3`
- **Bail reason**: `redacted`
- **Run ID**: `FFA60F3E-380A-4E8F-A322-FE82E79F9D3D`
- **Branch**: `unknown`
- **PR URL**: `unknown`

## Root-cause finding

verdict=larch-defect
confidence=high
summary=Step 4 commit-route skips new lint-fix edits once the dispatcher has committed, leaving the tree dirty before the 4.r rebase check

## Observation

During this run, Step 3's `checks repair-loop` ran `checks lint-fix` to fix a ruff and pyright failure. Lint-fix modified three files. `git status --porcelain=v1` showed them still uncommitted right after lint-fix finished:

```
 M python/larch/rendering/rendering.py
 M python/larch/report/tokens.py
 M python/larch/review/plan_review_panel.py
```

The Step 3 composite re-run then printed:

```
⏩ 4: commit (impl) status=skip reason=dispatcher-committed sha=a211ab9d4 elapsed=0s
```

`sha=a211ab9d4` is the original Codex implementer commit from Step 2, made before lint-fix ran. No new commit captured the lint-fix edits. The same composite run then failed the 4.r rebase checkpoint:

```
REBASE_OUTCOME=failed
REBASE_ERROR=error: cannot rebase: You have unstaged changes. error: Please commit or stash them.
```

## Root cause

`python/larch/implement/dispatch_commit_route.py`, `_run_step4_commit_leg` (around lines 684-689):

```python
seed_file = implement_tmpdir / "ship-seed-input.env"
manifest_path = _read_kv_file(path=seed_file, key="MANIFEST_PATH", default="").strip()
dispatcher_committed = _read_kv_file(path=seed_file, key="DISPATCHER_COMMITTED", default="").strip() == "true"
if dispatcher_committed and manifest_path and _path_readable_nonempty(Path(manifest_path)):
    return _step4_noop("dispatcher-committed")
```

This check reads a persisted `DISPATCHER_COMMITTED` flag and never inspects current `git status`. Once an external implementer has committed once, every later `checks-commit-route` re-entry in the same run takes this noop path unconditionally, even when the working tree has since changed.

`python/larch/implement/checks_lint_fix.py:443` tells the lint-fix agent explicitly: `"Do NOT commit; the parent script owns staging and commits."` Lint-fix relies on the caller (`checks-commit-route`'s Step 4 leg) to commit its edits. On the external-implementer path, that caller never does, because the `dispatcher_committed` shortcut fires first. The 4.r rebase checkpoint runs immediately after and fails on the dirty tree left behind.

By contrast, the recovery-path branch of the same function (the `already-committed` noop a few lines below) does call `_pathspec_clean_relative_to_head()` before returning noop. The `dispatcher_committed` shortcut has no equivalent cleanliness check.

## Scope

This reproduces whenever an external implementer (Codex or Cursor) completes Step 2, and a later Step 3 checks failure triggers `checks lint-fix` with autofixable findings, on any `/implement` run past Step 2. It is not specific to issue #6158's plan content.



## Attempts

| Attempt | Class | Resume hint | Outcome | UTC |
|---|---|---|---|---|
| none | n/a | n/a | n/a | n/a |

## Test plan
(no test plan section in plan-file)
