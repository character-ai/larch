## Goal
Implement issue #3364: [IMPLEMENTING] Versioning Overhaul Phase 1: Remove per-PR bump + CHANGELOG from /implement\n\n# Versioning Overhaul Phase 1 — Remove per-PR version bump + CHANGELOG from the `/implement` hot path.

## Implementation Plan
## Plan

Versioning Overhaul Phase 1 — stop `/implement` from writing a per-PR version bump and a `CHANGELOG.md` entry. Subtractive change: remove the bump/CHANGELOG writes at the source, physically remove the now-dead re-bump limbs and exit-5 bump-recovery escapes, neutralize the bump gates/hooks, retire the bump-specific NEVER-rules / invariants / reference docs, and mirror the change in the live-by-Phase-7 `python/` rework. Keep `ship-pr.sh`'s CI-fix rebase + force-push core. Physical deletion of the standalone bump/CHANGELOG **scripts** stays deferred to Phase 5. Diff is deletion-heavy (not mechanical churn).

> **Design-run note:** the external review panel was unavailable this design run (Codex exit 7, Cursor empty), so this plan was operator-approved at Gate C without external plan-review findings. `/implement` should treat the plan as un-reviewed-by-panel and apply extra scrutiny.

### UPDATED: `scripts/ship-pr.sh`
Remove all version-bump and CHANGELOG machinery from the live ship path; keep the CI-fix rebase core.
- Delete the main bump path: the `HAS_BUMP` branch that runs `classify-bump.sh` → `apply-bump.sh` → `check-bump-version.sh --mode post` (the `run_bump_phase` body). Advance the bump phase directly to the next phase (no classify/apply/verify).
- Delete the re-bump helper functions: `ship_pr_record_old_bump_version`, `ship_pr_changelog_ready_after_rebump`, `ship_pr_rebump_bullets_path`, `ship_pr_stage_rebump_bullets`, `ship_pr_commit_changelog_after_rebump`, plus the bump-reasoning rewrite helpers `rewrite_reasoning_new_version` / `write_corrected_reasoning_fallback` and the drop-bump / drop-changelog / `semver_lt` wrappers used only by the re-bump path.
- In `_run_rebase_rebump_from_step3`: remove the `classify-bump.sh` / `apply-bump.sh` re-bump block and the `ship_pr_commit_changelog_after_rebump` call. Keep fast-forward of local main, conflict handling, force-push.
- In `run_rebase_rebump`: remove the `ship_pr_record_old_bump_version` / drop-bump / `ship_pr_stage_rebump_bullets` limbs. Keep fetch, rebase-onto-main, conflict resolution, `--resume-phase ship-pr-rrr-phase14` re-entry, and force-push (the CI-fix capability the issue mandates preserving).
- Remove the exit-5 bump-recovery escapes: the `RESUME_PHASE bump CALLER_KIND step8_apply_bump_same_version` set on apply-bump failure, and the force-push-gate `CALLER_KIND step8b_rebase; exit 5` escape. Keep the `ship_pr_pre_push` exit-5 conflict path.
- Prune now-dead state keys (`HAS_BUMP`, `BUMP_TYPE`, `NEW_VERSION`, `BUMP_REASONING_FILE`, `step8*` `CALLER_KIND` values) from `write_initial_state`, the `state_set_many` / persisted-key lists, and the state echo. Keep `RESUME_PHASE` / `CALLER_KIND` (still used by `ship_pr_pre_push` / `ship-pr-rrr-phase14`).
- Edge: the `bump-branch-guard` branch-alignment backstop lives inside `run_bump_phase`. Relocate the branch-alignment assertion to a surviving pre-push checkpoint, or explicitly accept its loss — do not silently drop branch safety with the bump.
- Sibling: update `scripts/ship-pr.md`.

### UPDATED: `scripts/implement-finalize.sh`
Remove the Step 8a CHANGELOG step and the `postbump` bump-verification glue.
- Remove `maybe_update_changelog` and its helpers (`collect_changelog_bullets`, `changelog_categories_to_markdown`, the `check-changelog-present.sh` / `commit-changelog.sh` calls), and its caller in the `postbump` path.
- Remove the `postbump` glue depending on `HAS_BUMP` / `NEW_VERSION` / `check-bump-version.sh --mode post`; `postbump` keeps only its non-bump responsibilities. Reconcile `CHANGELOG_STATUS` reporting.
- Sibling: update `scripts/implement-finalize.md`.

### UPDATED: `skills/implement/SKILL.md`
- Step 8: drop "version bump" from the Step-8+ description and end-to-end summary; remove the post-/bump-version boundary directives and sub-steps 3/3b.
- Step 8a: remove the CHANGELOG section and its rebase-time re-application notes.
- Step 8b / exit-code table: reconcile the Step 8+ exit-code matrix. Remove the Exit-5 `step8b_rebase` / `step8_apply_bump_same_version` branches (keep `ship_pr_pre_push`). Remove the Rebase + Re-bump Sub-procedure invocation.
- NEVER-rules: retire **#8** (step8b_rebase caller_kind), **#11** (no `/bump-version` Skill in Step 8 + no `✅ 8:` breadcrumb), **#15** (no end-turn after `/bump-version` in sub-procedure). Renumber/gap consistently with `test-implement-structure.sh`. Keep **#19**.
- `## Load-Bearing Invariants`: retire Invariant **#1** (version-bump freshness) and **#3** (degraded-git fail-closed) for the `/implement` path — remove the assertions, do not merely bypass.
- Repoint references to the two stubbed reference docs.

### REWRITTEN: `skills/implement/references/rebase-rebump-subprocedure.md`
Replace the 198-line body with a short retirement stub: "Retired in Phase 1 (#3364); `/implement` no longer bumps or writes CHANGELOG; standalone scripts deleted in Phase 5."

### REWRITTEN: `skills/implement/references/bump-verification.md`
Replace the 70-line body with the same retirement stub pattern.

### UPDATED: `skills/implement/scripts/hook-post-bump-version.sh`
Neutralize to a documented inert early-exit stub ("retired in Phase 1; deleted in Phase 5"); keep `hooks/hooks.json` registration (no-op hook). Sibling: `hook-post-bump-version.md`.

### UPDATED: `skills/implement/scripts/hook-stop-fail-close.sh`
Remove the `.bump-version-armed` / `postbump-state.sh` mid-Step-8 block (never arms once bump is gone). Keep the post-/review boundary block. Sibling: `hook-stop-fail-close.md`.

### UPDATED: `python/rebase.py`
Mirror the bash subtractive change.
- Drop `import changelog` and `import version_bump`.
- Remove the re-bump/changelog limbs: `_stage_rebump_bullets`, `_commit_changelog_after_rebump`, `_changelog_ready_after_rebump`, `_rebump_bullets_path`, `_parse_bump_version_from_sha`, the `_BUMP_SUBJECT_RE` / `_CHANGELOG_BASENAMES` constants used only by those, the drop-bump call, and the `if has_bump:` classify/apply/commit-changelog block in `rebase_and_rebump`.
- Remove the `has_bump` parameter; keep `defer_push`, fetch, rebase, `_resolve_conflicts`, `_sync_local_main`, force-push.
- `python/config.py`, `python/merge.py`, and `python/{version_bump,changelog,bump_worktree}.py` are unchanged (dormant, Phase-5 parity; constants still referenced by the dormant modules + `test_config.py`; same-version merge gate self-disables).

### UPDATED: `python/test_rebase.py`
Drop the re-bump/changelog-path assertions; keep rebase/conflict/force-push coverage. `make py-lint` + `make py-test` green.

### UPDATED: `skills/implement/scripts/test-step-8a-changelog.sh`
Step 8a is removed. Repurpose to assert the absence of changelog writes, or remove it and drop its `Makefile` `test-step-8a-changelog` target + shard entry. Sibling: `test-step-8a-changelog.md`.

### UPDATED: `scripts/test-implement-finalize.sh`
Update assertions for the removed changelog/bump glue. Sibling: `scripts/test-implement-finalize.md`.

### UPDATED: `scripts/test-implement-structure.sh`
Update SKILL.md structural assertions (removed NEVER #8/#11/#15, removed Step 8a, reconciled exit-code table, retired Invariant #1/#3). Re-check `scripts/test-implement-anti-halt.sh` for NEVER #15 fixtures. Sibling: `scripts/test-implement-structure.md`.

### UPDATED: `docs/workflow-lifecycle.md`
Per `.claude/rules/drift-prone-prose-in-docs.md`, grep `docs/`, `README.md`, and `.claude/skills/bump-version/SKILL.md` for prose claiming `/implement` bumps the version / writes CHANGELOG and update it. `.github/workflows/release-tag.yaml` stays untouched (Phase 4).

### Approach
1. Stop the writes at the source first (`ship-pr.sh` bump phase + `implement-finalize.sh` Step 8a).
2. Physically remove the now-dead live code (re-bump limbs, `_run_rebase_rebump_from_step3` re-bump block, exit-5 escapes); keep the CI-fix rebase + force-push.
3. Retire the prose (NEVER #8/#11/#15, Invariant #1/#3, stub the two reference docs).
4. Neutralize the gates/hooks (remove check-*/commit-changelog call sites; inert-stub `hook-post-bump-version.sh`; drop the `.bump-version-armed` block).
5. Mirror in `python/rebase.py`; leave `config.py` / `merge.py` / standalone modules dormant.
6. Standalone scripts (`apply-bump.sh`, `classify-bump.sh`, `commit-changelog.sh`, `check-bump-version.sh`, `check-changelog-present.sh`) + their `test-*` harnesses stay on disk, dormant (Phase 5 deletes them).
7. Keep edits minimal inside `run_rebase_rebump`'s CI-fix core (#3334/#3335 both CLOSED, but the loop is shared territory).

### Edge cases
- `bump-branch-guard`: relocate the branch-alignment assertion out of the deleted bump phase, or explicitly accept its loss.
- `release-tag.yaml`: idempotent; degrades to a harmless no-op once the version freezes. No Phase-1 change.
- Stale `ship-pr-state.sh` resume keys (`HAS_BUMP=true`, `RESUME_PHASE=bump`) from pre-upgrade runs must not crash the removed phase — tolerate-and-ignore.
- Forked-target dry-run already skips changelog; do not regress fork behavior.

### Failure modes
1. Half-removed bump leaves a dangling state key / call site → `ship-pr.sh` errors under `set -euo pipefail`. Mitigate: grep for every `HAS_BUMP` / `NEW_VERSION` / `classify-bump` / `apply-bump` token and confirm zero live references.
2. CI-fix rebase regression if removal over-reaches into the rebase/force-push core. Mitigate: keep `run_rebase_rebump` / `rebase.py` fetch+rebase+resolve+force-push intact; assert in `test-rebase-push-*` / `test-implement-rebase-macro`.
3. Stale prose drift (a NEVER-rule/doc still asserts bump). Mitigate: docs-sync sweep + `make lint`.

### Testing strategy
- Bash: update `test-implement-structure.sh`, `test-implement-finalize.sh`, `test-step-8a-changelog.sh`; keep the standalone-script harnesses green unchanged.
- Python: update `test_rebase.py`; `make py-lint` + `make py-test` green.
- Repo: `bash scripts/relevant-checks.sh` / `make lint` green.
- Acceptance proof: a concurrency reproduction (two disjoint-skill PRs; B merges after A) lands B with no rebase/re-bump and no bump/CHANGELOG mutation.

## Acceptance

- A concurrency reproduction — two PRs touching disjoint skills, B merging after A — merges the second PR **without** any rebase/re-bump.
- No `Bump version to X.Y.Z` commit and no `CHANGELOG.md` mutation appear on `/implement` feature branches.
- `ship-pr.sh`'s CI-fix path still rebases + force-pushes when a fixer changes files after `main` advanced (`run_rebase_rebump` core retained; `ship_pr_pre_push` exit-5 conflict path retained).
- `ship-pr.sh` `ship_pr_*_rebump` limbs and the Step 8+ exit-5 `step8b_rebase` / `step8_apply_bump_same_version` escapes are removed; dead bump state keys pruned.
- `skills/implement/SKILL.md` NEVER #8/#11/#15 and Load-Bearing Invariant #1/#3 retired; Step 8/8a/8b contract and exit-code table internally consistent; `rebase-rebump-subprocedure.md` and `bump-verification.md` reduced to retirement stubs.
- `python/rebase.py` re-bump/changelog limbs removed (CI-fix core kept); `python/config.py` / `merge.py` / `version_bump.py` / `changelog.py` unchanged.
- `make lint` green; `make py-lint` / `make py-test` green; updated harnesses (`test-implement-structure`, `test-implement-finalize`, `test-step-8a-changelog`, `python/test_rebase.py`) green.
- Standalone bump/CHANGELOG scripts remain on disk, dormant (physical deletion deferred to Phase 5).
- **Acceptance correction:** the issue's "`ship-pr.sh` / `test-ship-pr*` harnesses updated and green" line is stale — `test-ship-pr*.sh` was removed in #3335. The green-after harness set is the one listed above plus `make lint` / `make py-test`.

diff_lines: 1230

## Test plan
(no test plan section in plan-file)
