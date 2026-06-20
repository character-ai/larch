## Goal
Implement issue #4847: [IMPLEMENTING] [BUG] /design plan-review-loop postplan validator wrong cwd (recurrence of #4490).

## Implementation Plan
## Summary

In `/design` Step 3 plan review (loop mode), the plan-review **loop** runs its postplan plan-command validator from the **plugin-cache** working directory instead of the consumer repo. The validator's consumer-repo-root derivation then fails, so its dual-root script-existence check searches only the plugin cache. Consumer-repo scripts that are absent from the installed plugin-cache version are falsely reported as `missing-script`, which forces a spurious `STEP3_REVIEW_LOOP_STATUS=postplan-operator-required` bail (`POSTPLAN_RC=10`) and an operator Override to continue. This is a recurrence of #4490 in a code path that #4490's fix did not cover; same wrong-cwd-in-loop family as #4509.

## Original report

Observed on a live `/design` run (larch 51.1.9). After the Step 3 plan-review loop applied an accepted finding and re-emitted the plan, the postplan plan-command validator reported 2 false `missing-script` defects and bailed to `postplan-operator-required`:

```
DEFECT script=skills/implement/scripts/test-step-18.sh kind=missing-script
DEFECT script=skills/implement/scripts/test-step-7a.sh kind=missing-script
```

Both scripts exist in the consumer repo being designed (`skills/implement/scripts/test-step-18.sh`, `skills/implement/scripts/test-step-7a.sh`). The accepted finding had just expanded the plan to reference `test-step-7a.sh`; `test-step-18.sh` was already referenced from the initial draft. The Step 2b postplan validated cleanly on the same run.

Related but already tracked (do not duplicate): #4841's dynamic-slot scaffold symptom also recurred on this run (`COLLECT_FAILURE_COUNT=6` — all dynamic scout slots dropped `NOT_SUBSTANTIVE` — vs `COLLECT_OK_COUNT=8` static). #4841 is OPEN and separate from this defect.

## Reproduction scenario

1. Install larch as a released plugin, so the plugin cache (e.g. `~/.claude/plugins/cache/larch-local/larch/51.1.9`) lags the consumer dev repo.
2. Run `/design <issue>` on an issue whose Step 3 plan-review loop revises the plan to reference a consumer-repo-only script that is absent from the installed plugin-cache version (for example a test harness like `skills/implement/scripts/test-step-7a.sh` added to the dev repo after the release was cut).
3. The loop re-emits the plan and runs postplan validation. The validator reports `missing-script` for the consumer-only script and the loop bails to `postplan-operator-required` (`POSTPLAN_RC=10`), even though the script exists in the repo being designed.

Contrast: the Step 2b postplan (run from the consumer-repo cwd) validates the same script cleanly. The divergence isolates the defect to the loop's working directory.

## Expected behavior

The Step 3 plan-review-loop postplan validator should resolve script paths against the **consumer repo** being designed (with the plugin cache as the secondary dual-root for plugin-only scripts), exactly as the Step 2b postplan does. A consumer-repo script referenced in the plan should not be reported `missing-script` merely because it is absent from the installed plugin-cache version. The loop should not bail to `postplan-operator-required` on this false positive.

## Observed behavior

The loop validator resolves only against the plugin cache. Consumer-only scripts are reported `missing-script`, producing `VALIDATE_STATUS=defects-found` and a spurious `postplan-operator-required` bail that halts the run for operator intervention.

## Root cause analysis

The plan-review loop forces every subprocess working directory to the plugin-cache root, which breaks the consumer-repo-root derivation that #4490 added to the postplan validator.

1. `python/plan_review.py:30` — `_REPO_ROOT = Path(__file__).resolve().parents[1]`. Because `plan_review.py` is loaded from the plugin cache (`CLAUDE_PLUGIN_ROOT`), `_REPO_ROOT` is the plugin-cache root, not the consumer repo.
2. `python/plan_review.py:879` — `_run_command(...)` runs `subprocess.run(argv, cwd=str(_REPO_ROOT), ...)`. Every loop subprocess inherits the plugin-cache cwd, including the postplan-emit invocation built at `python/plan_review.py:854` (`design postplan-emit --with-plan-size`).
3. `python/design_postplan.py:26-37` — `_consumer_repo_root()` derives the consumer repo via `git -C <Path.cwd()> rev-parse --show-toplevel`. With cwd forced to the plugin cache (which is not a git checkout), git exits non-zero and the helper returns `None`.
4. `python/design_postplan.py:214-227` (the #4490 dual-root fix) — `repo_root_arg = _consumer_repo_root() or root`, where `root` is `CLAUDE_PLUGIN_ROOT`. With `_consumer_repo_root()` `None`, `repo_root_arg` collapses to the plugin cache, and the validator is also handed `CLAUDE_PLUGIN_ROOT` = the plugin cache.
5. `python/plan_quality.py` (`_normalize_token`, ~528-543; missing-script determination ~821-846) — the dual-root existence check iterates over `(plugin_root, repo_root)`. Both are now the plugin cache, so it searches only the cache. Scripts present in the consumer repo but absent from the cache are flagged `missing-script`.

Why #4490's fix is incomplete: #4490 made `design_postplan.py` derive the consumer repo from cwd and pass `--repo-root` plus a dual-root `CLAUDE_PLUGIN_ROOT`. That works when the postplan process inherits the consumer-repo cwd (Step 2b). The Step 3 plan-review loop defeats it by forcing the subprocess cwd to `_REPO_ROOT` (the plugin cache). This is the same wrong-cwd-in-loop class as #4509 (dirty-tree checkpoint).

## Evidence

- `$DESIGN_TMPDIR/validate-plan-commands.log`: two `DEFECT … kind=missing-script` lines for `test-step-18.sh` and `test-step-7a.sh`.
- `$DESIGN_TMPDIR/.design-postplan-emit-result.env`: `VALIDATE_STATUS=defects-found`, `VALIDATE_DEFECT_COUNT=2`.
- `$DESIGN_TMPDIR/.step3-review-result.env`: `STEP3_REVIEW_LOOP_STATUS=postplan-operator-required`, `POSTPLAN_RC=10`.
- Step 2b postplan on the same run emitted `VALIDATE_STATUS=ok` (ran from the consumer-repo cwd).
- Filesystem checks against the 51.1.9 plugin cache: the cache is not a git checkout, and both flagged scripts are absent from it, while the source `step-18.sh` / `step-7a.sh` are present. Both `test-step-18.sh` and `test-step-7a.sh` exist in the consumer repo.
- `python/plan_review.py:30` (`_REPO_ROOT` = plugin cache), `:854` (postplan-emit argv), `:879` (`cwd=str(_REPO_ROOT)`).
- `python/design_postplan.py:26-37` (`_consumer_repo_root` via `git -C cwd`), `:214-227` (the #4490 `repo_root_arg = _consumer_repo_root() or root` fallback).

## Affected files

- `python/plan_review.py` — primary fix site. `_REPO_ROOT` (line 30) is the plugin cache; `_run_command` (line 879) forces every loop subprocess to that cwd, including the postplan-emit at line 854.
- `python/design_postplan.py` — `_consumer_repo_root()` (lines 26-37) silently degrades to the plugin cache when cwd is not a git checkout; the dual-root fallback (lines 214-227) then loses the consumer root.
- `python/plan_quality.py` — the dual-root existence check (`_normalize_token` ~528-543; missing-script verdict ~821-846) only searches the roots it is given, so it inherits the wrong-cwd collapse.

## Suggested fix(es)

- Thread the consumer repo root into `python/plan_review.py` and run the postplan-emit (and any validator) subprocess with `cwd` = the consumer repo, not `_REPO_ROOT`. Capture the consumer repo root at loop entry before any cwd change (for example `git rev-parse --show-toplevel` from the invoking cwd, or accept it via an env handoff such as the value already used elsewhere in the run), then either set it as the subprocess cwd or pass `--repo-root <consumer>` explicitly to `design postplan-emit`.
- Audit the other `python/plan_review.py` `_run_command` call sites (the loop runs many subprocesses with `cwd=str(_REPO_ROOT)`) for the same wrong-cwd class, consistent with #4509.
- Regression test: assert the loop postplan-emit runs with the consumer-repo cwd, or that a consumer-only script referenced in the plan does not produce `missing-script` when the plugin cache lags the consumer repo (simulate a plugin-cache root missing a script that exists in the consumer repo root).

## Open questions

- Should the fix set the consumer-repo cwd for all `_run_command` subprocesses in the loop, or only the validator/postplan path? A blanket cwd correction would also close the #4509-class siblings, but should be checked against any loop subprocess that legitimately depends on the plugin-cache cwd.
- Is the consumer repo root already available to the loop via an existing env/handoff (so it need not re-derive it), or must it be captured and passed at loop entry?

## Test plan
(no test plan section in plan-file)
