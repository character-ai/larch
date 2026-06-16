## Goal
Implement issue #4490: [IMPLEMENTING] [BUG] /design postplan validator uses plugin cache as --repo-root, falsely flags consumer-repo scripts.

## Implementation Plan
## Summary

During `/design` Step 3 plan review, accepted reviewer findings may revise the plan to include bash fences referencing scripts that exist in the consumer repo but not in the larch plugin cache. `design_postplan.py` passes `root = _plugin_root()` as `--repo-root` to `plan validate`. When the plugin cache copy of the repo is used as the root, scripts present only in the consumer repo are flagged as `kind=missing-script` or `kind=non-canonical-path`, causing `POSTPLAN_RC=10` and a `postplan-operator-required` bail to the main agent even when the plan is correct.

## Reproduction

1. Run `/design` on an issue in a consumer repo that is itself the larch source tree (or any case where the consumer repo has more scripts than the cached plugin copy).
2. A reviewer acceptance revises the plan to include a bash fence such as:
   ```bash
   bash skills/implement/scripts/test-stall-recovery-report-1.sh
   ```
3. The script exists in the consumer repo but is absent from the plugin cache (`~/.claude/plugins/cache/larch-local/larch/50.1.4/`).
4. Postplan validation (run by the plan review loop after applying accepted findings) calls `design_postplan.py`, which passes `--repo-root <plugin-cache-dir>` to `plan validate`.
5. Validator resolves the path relative to the plugin cache root, does not find the file, and emits `DEFECT script=skills/implement/scripts/test-stall-recovery-report-1.sh kind=missing-script`.
6. Loop returns `STEP3_REVIEW_LOOP_STATUS=postplan-operator-required` with `POSTPLAN_RC=10`.

## Evidence from live session

```
validate-plan-commands.log:
  DEFECT script=skills/implement/scripts/test-stall-recovery-report-1.sh kind=missing-script
  VALIDATE_STATUS=defects-found  DEFECT_COUNT=1
```

Manual check confirmed the file exists in the consumer repo at `skills/implement/scripts/test-stall-recovery-report-1.sh` (51 241 bytes, executable). The plugin cache at `50.1.4/skills/implement/scripts/` has 71 scripts but does not include this one.

## Root cause

`design_postplan.py` line ~93:
```python
root = _plugin_root()   # returns CLAUDE_PLUGIN_ROOT or __file__.parents[1]
```

Then at line ~196:
```python
"--repo-root",
str(root),             # <-- plugin cache dir, not consumer repo
```

`plan_quality.py`'s `validate_commands()` does have a `consumer_repo` fallback at line ~1851 that detects the CWD git repo, but that path is bypassed when `--repo-root` is explicitly supplied.

## Severity

Every `/design` run where accepted findings add a `bash skills/implement/scripts/*.sh` command in a bash fence will produce a spurious validator defect. The operator must either: (a) invoke Fix-and-retry and manually edit the plan to remove the bare bash invocation, or (b) choose Override. Both add friction and burn reviewer rounds.

## Suggested fix

**Option A (preferred)**: In `design_postplan.py`, detect the consumer repo root via `git -C os.getcwd() rev-parse --show-toplevel` and pass it as `--repo-root` when available, falling back to `_plugin_root()` only when no consumer git repo is found.

**Option B**: In `plan_quality.py` `validate_commands()`, when a script flagged as `missing-script` is not found under the explicit `--repo-root`, try one additional lookup under `_git_repo_root(Path.cwd())` before emitting the defect. This keeps `design_postplan.py` unchanged.

**Option C**: Add a `--consumer-repo-root` flag to `plan validate` that takes priority over `--repo-root` for script existence checks, keeping plugin-root handling for flag validation.

Note: the immediate workaround for plan authors is to express optional local-run commands as inline code spans rather than bash fences, so the validator does not parse them as plan commands.

## Test plan
(no test plan section in plan-file)
