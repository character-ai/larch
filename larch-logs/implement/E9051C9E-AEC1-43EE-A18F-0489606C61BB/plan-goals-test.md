## Goal
Implement issue #5930: [IMPLEMENTING] [BUG] postbump/_rebase_no_push stalls unconditionally on rebase conflicts (no CONFLICT_FILES, no auto-resolution for generated files).

## Implementation Plan
## Summary

`postbump`'s pre-PR rebase gate (`python/larch/state/finalize.py::_rebase_no_push`, called from `postbump`) runs a plain `git rebase <base>/main` with no conflict-file capture and no auto-resolution, and unconditionally stalls (`STALL_STEP=rebase-failed`) on any non-zero rebase result — including trivially-regeneratable conflicts in shared generated files such as `python/skill-closure-baseline.json`. This is a documented "accepted degradation" (`skills/implement/SKILL.md` line 91), but the underlying gap has no open tracking issue, and fresh evidence from this run shows it is a real, recurring, mechanically-resolvable failure mode rather than a rare edge case.

## Original report

Root-cause and file a bug for a /implement stall hit on issue #5880 (run RUN_ID=A18B5AE3-ADDC-4414-B0C3-42EC7C0F29F9, tmpdir claude-implement-larch3-bhoavxqe).

`/implement --merge 5880`'s Step 8 (ship PR) stalled twice in a row with `PHASE=rebase-failed` / `STALL_STEP=rebase-failed`, classified by the automated stall-recovery classifier as `FAILURE_CLASS=transient-infra` then `FAILURE_CLASS=same-cause-repeat` (`MAX_ATTEMPTS=2` reached), requiring operator takeover. Taking over, I fetched `origin/main` and manually reran the rebase as the documented recovery path prescribes ("operators must resolve these Step 8b rebase conflicts manually") — it failed with a real, deterministic content conflict in `python/skill-closure-baseline.json`, which I resolved by running `make regen-skill-closure-baseline` and staging the result, then completed the rebase and re-dispatched Step 8 successfully (PR #5928 merged).

## Reproduction scenario

1. Start `/implement --merge <issue>` on a plan that touches any `skills/shared/*.md` or `skills/design/**`/`skills/implement/**` file that feeds `python/skill-closure-baseline.json` (i.e. any plan requiring `make regen-skill-closure-baseline`).
2. While Step 8 (ship PR) is about to run `postbump`, have a *different* concurrent `/implement` run on the same repo merge a PR that also touches `python/skill-closure-baseline.json` (common in this repo: many parallel md-to-py prose-compression tasks regenerate this same shared baseline file).
3. `postbump` calls `_rebase_no_push`, which runs `git rebase origin/main`. The rebase conflicts in `python/skill-closure-baseline.json` (both sides modified the same generated JSON).
4. `_rebase_no_push` unconditionally runs `git rebase --abort` and returns `"failed"`; `postbump` reports `FinalizeResult(Outcome.STALLED, "rebase-failed", "rebase failed", ...)` with no `CONFLICT_FILES` and no indication the conflict is in a known-trivial, mechanically-regeneratable file.
5. The run stalls; Step 18a stall-recovery classifies it `transient-infra` / `step8-shippr` and retries up to `MAX_ATTEMPTS=2`, but each retry re-fetches `origin/main` (which keeps advancing under concurrent write load) and can hit the same conflict again, exhausting retries as `same-cause-repeat` and requiring manual operator intervention every time.

This exact sequence occurred on this run: two automated retries both failed generically, and manual intervention (fetch + rebase + `make regen-skill-closure-baseline` + stage + continue) was required to unblock it.

## Expected behavior

When `postbump`'s pre-PR rebase conflicts are confined to a small set of known-generated, mechanically-regeneratable files (starting with `python/skill-closure-baseline.json`), the driver should be able to auto-resolve them (e.g. abort, regenerate the baseline fresh post-rebase, and continue) without stalling and requiring a human/agent operator to manually intervene on every occurrence. At minimum, the stall should carry `CONFLICT_FILES` so an operator (or a future automated fixer) does not have to rediscover which file conflicted and how to resolve it from scratch.

## Observed behavior

`_rebase_no_push` (`python/larch/state/finalize.py`, `postbump` caller around lines 282-380) treats every non-zero rebase result identically: it aborts the rebase and returns the literal string `"failed"`, with no distinction between a trivial, auto-resolvable conflict and a hard semantic conflict, and no `CONFLICT_FILES` capture at all. `postbump` then reports a generic `Outcome.STALLED` / `"rebase-failed"`. This is already accurately documented as an "accepted degradation" in `skills/implement/SKILL.md` line 91 (fixed for documentation-accuracy by issue #5839, which restored the correct `transient-infra` / `step8-shippr` / manual-resolution description after a prose-compression pass had briefly made the docs claim an automated `merge-conflict` recovery class that does not exist in code). That issue was about the *documentation* being wrong; this bug is about the *underlying behavior gap* the (now-accurate) documentation describes.

## Root cause analysis

`python/larch/state/finalize.py::_rebase_no_push` (called from `postbump`) is a narrow, no-fixer rebase gate:

```python
def _rebase_no_push(runner, *, base_remote, cwd):
    if not _retry_fetch(runner=runner, remote=base_remote, ref="main", cwd=cwd):
        return "failed"
    base = f"{base_remote}/main"
    if git.is_ancestor(runner, base, "HEAD", cwd=cwd):
        return "already-fresh"
    result = git.rebase(runner, base, cwd=cwd)
    if result.returncode == 0:
        return "rebased"
    _ = git.rebase(runner, "--abort", cwd=cwd)
    return "failed"
```

Unlike the sibling CI-fix rebase path (`ship_pr_pre_push` / `RESUME_PHASE=ship-pr-rrr-phase14`, `run_rebase_rebump` in `python/rebase.py`), which gained a `PrePushConflictHandoff` exception carrying `conflict_files`/`resume_phase`/`caller_kind` via issue #3404, `_rebase_no_push` has never had equivalent treatment. It was presumably left alone because it is the *first*, simplest rebase gate in the ship-pr state machine and pre-dates the CI-fix waterfall machinery, but that also makes it the *most frequently hit* rebase checkpoint (every single `/implement --merge` run reaches it, versus the CI-fix path which only triggers after a PR already exists and CI needs a fix).

The specific conflict encountered in this run — `python/skill-closure-baseline.json` — is explicitly classified as an auto-resolvable "generated file" by the existing Conflict Resolution Procedure (`skills/implement/references/conflict-resolution.md`, Phase 1, "Generated files": "If the file is auto-generated and both sides are obvious, classify as trivial and auto-resolve immediately"). But that procedure is only wired up for two caller families (`early_rebase` and `ship_pr_pre_push`); `postbump`'s plain pre-PR gate is not one of them, so it has no path to that auto-resolution logic at all.

Given this repo's `origin/main` write velocity — 6+ merged commits observed in well under 15 minutes during this single recovery, many from concurrent `/implement`/`/design` prose-compression runs that regenerate the same shared baseline file — this specific conflict is likely to recur often.

## Evidence

- `python/larch/state/finalize.py`: `_rebase_no_push` and its caller `postbump` (STALLED/"rebase-failed" on any non-zero rebase, no `CONFLICT_FILES`).
- `skills/implement/SKILL.md` line 91: "Step 8b force-push-gate rebase conflicts (accepted degradation): when the active Python driver hits a Step 8b rebase conflict, it stalls (`STALL_STEP=rebase-failed`) without `CONFLICT_FILES` or `conflict-resolution.md` handoff. Operators must resolve these Step 8b rebase conflicts manually..."
- Issue #5839 (closed/done): confirms `transient-infra` / `step8-shippr` is the real classification (`python/larch/state/_classify.py` lines ~123-124) and that no automated `merge-conflict` recovery class exists in code — a pure documentation-accuracy fix, not a behavior change.
- Issue #3404 (closed/done): added `PrePushConflictHandoff` (`conflict_files`, `resume_phase`, `caller_kind`) to the *different*, later CI-fix rebase-rebump path in `python/rebase.py`; explicitly out of scope there: "No edits to `scripts/ship-pr.sh`, `skills/implement/references/conflict-resolution.md`, or `skills/implement/SKILL.md`" and no mention of `postbump`/`_rebase_no_push`.
- This run's `stall-recovery-root-cause.md` (session-local artifact, not committed): confirms two consecutive `rebase-failed` stalls (`FAILURE_CLASS=transient-infra` then `same-cause-repeat`, `RESUME_HINT=step8-shippr` then `none`, `MAX_ATTEMPTS=2` reached) before requiring operator takeover.
- Direct reproduction: `git fetch origin main && git rebase origin/main` on the stalled branch (`sergey-zhupanov/implementing-md-to-py-x-prose-compress-s-5880`) failed with `CONFLICT (content): Merge conflict in python/skill-closure-baseline.json`; running `make regen-skill-closure-baseline` (which just runs `python3 python/cli.py lint skill-closure-growth --write`, a pure regeneration from the working tree, not a textual merge) and staging the result resolved it cleanly, and `git rebase --continue` completed the remaining 4 commits without further conflict.
- Dedup search performed (open+closed issues): "rebase-failed Step 8b", "CONFLICT_FILES postbump", "_rebase_no_push", "postbump PrePushConflictHandoff", "accepted degradation Step 8b conflict" — only closed issues found (#5839 docs fix, #3404 different code path, #2531/#2559 the old retired bash-era `step8b_rebase` from before the versioning-overhaul Phase 1 removed per-PR bumps). No open issue currently proposes fixing/improving this specific gate.

## Affected files

- `python/larch/state/finalize.py` — `_rebase_no_push` / `postbump`: the code path with no conflict-file capture or auto-resolution.
- `skills/implement/SKILL.md` (line 91 area) — documents the gap as accepted; would need updating if behavior changes.
- `skills/implement/references/conflict-resolution.md` — the existing Phase 1-4 procedure (including the "Generated files" trivial-auto-resolve rule) that a fix could extend to this caller family, or reuse a narrower subset of.
- `python/rebase.py` — sibling `PrePushConflictHandoff` implementation from #3404, useful as a reference pattern.
- `python/skill-closure-baseline.json` — the specific shared generated file that conflicted in this run; likely the single highest-value target for a narrow, low-risk first fix (auto-regenerate-and-retry before giving up).

## Suggested fix(es)

Two independent options, not mutually exclusive:

1. **Narrow, low-risk**: in `_rebase_no_push`, when the rebase fails, check whether the conflicted paths are a known allow-list of generated files (starting with just `python/skill-closure-baseline.json`); if so, regenerate them post-rebase-abort-and-retry (mirroring `make regen-skill-closure-baseline`'s logic, i.e. `python3 python/cli.py lint skill-closure-growth --write`) and continue, instead of stalling. This directly addresses the conflict actually observed in this run and in the precedent mentioned in this run's own investigation (an earlier Step 7a checkpoint conflict in the same file, resolved the same way).
2. **General**: give `postbump`/`_rebase_no_push` a `PrePushConflictHandoff`-style exception (mirroring #3404's pattern in `python/rebase.py`) carrying `conflict_files`, so a real `CONFLICT_FILES`-driven Conflict Resolution Procedure invocation can run for this caller family too, instead of an unconditional stall. This is a bigger change (new caller family in `conflict-resolution.md`, possible reviewer-panel wiring) but generalizes beyond the one known-generated-file case.

## Open questions

- Is there a reason `postbump`'s pre-PR gate was deliberately left out of the #3404 `PrePushConflictHandoff` work and the Conflict Resolution Procedure's caller-family list, beyond "it pre-dates that machinery"? If so, a narrow generated-file-only auto-resolution (option 1 above) may be preferred over extending the full procedure to a third caller family.
- Should the generated-file allow-list for auto-resolution live in `python/config.py` (single source of truth, similar to existing bump-file lists) so other call sites can reuse it if more shared generated files gain the same conflict pattern in the future?

## Test plan
(no test plan section in plan-file)
