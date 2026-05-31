### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/rebase.py (proposed step 5)
- **Concern**: Re-bump path omits bash guard when classify returns bump_type NONE. Scenario: scripts/ship-pr.sh:3074-3087 skips apply-bump and commit-changelog when bump_type is NONE; the plan always runs version_bump.apply_bump then _commit_changelog_after_rebump
- **Proposed resolution**: After a no-op classify (NONE), apply_bump may still rewrite plugin.json / add a redundant bump commit, and the CHANGELOG tail may run when bash would only sync and push Gate steps 5-6 on bump_type != "NONE" and non-empty new_version (mirror _run_rebase_rebump_from_step3); add a stub test for the NONE short-circuit

### FINDING_2:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:45-48 (Fetch + rebase)
- **Concern**: Fetch result is not checked before is_ancestor/rebase. Scenario: `git.fetch` failure leaves stale `base_remote/base_ref`; `is_ancestor` may short-circuit as already-fresh or `git rebase` runs on a stale base
- **Proposed resolution**: After fetch, non-zero exit → abort any in-progress rebase if needed and raise `Stalled` (or `TransientNetworkError` when signature matches bash); do not proceed to classify/push

### FINDING_3:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:101-103 (_resolve_conflicts step 5)
- **Concern**: `rebase --continue` failure paths are incomplete. Scenario: Non-zero continue with remaining `diff-filter=U` paths is not specified; implementers may `--skip` or exit while conflicts remain
- **Proposed resolution**: After failed continue, if unmerged paths exist re-enter the conflict loop; only `--skip` on empty-unmerged empty-commit signatures (parity with `git-rebase-skip.sh` / conflict-resolution.md)

### FINDING_4:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:101-103 (_resolve_conflicts step 5)
- **Concern**: Blanket `--skip` on any failed continue with empty unmerged set. Scenario: Real continue errors (hook failure, corrupt index) with no U paths could skip a bad commit and leave a broken history
- **Proposed resolution**: Gate `rebase_skip` on known empty/already-applied stderr patterns; otherwise `Stalled` and abort if the repo is left mid-rebase

### FINDING_5:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:92-97 (_resolve_conflicts)
- **Concern**: Fixer waterfall launch contract is underspecified. Scenario: `build_launch_argv`/`launch_tier` require `--output`, `--run-id`, `--repo`; optional `--plan-file` is used in bash (`plan_args`); plan only lists `--role` and `--conflict-files`
- **Proposed resolution**: Document the closure around injected `launch_fn`: temp output path, `plan_file` when available, then `run_waterfall`; tests should assert argv includes `--output` and optional `--plan-file`

### FINDING_6:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:56-60 (Re-classify / re-bump)
- **Concern**: No gate when `classify_bump` returns `NONE`. Scenario: Bash skips `apply-bump` and changelog tail when `BUMP_TYPE=NONE`; plan always calls `apply_bump` and `_commit_changelog_after_rebump`
- **Proposed resolution**: When `bump_type == "NONE"`, skip `apply_bump` and post-bump changelog; still allow force-push if that matches caller intent

### FINDING_7:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:37-44 (_stage_rebump_bullets)
- **Concern**: Missing benign path when `old_version` cannot be parsed. Scenario: Bash `ship_pr_stage_rebump_bullets` returns early on invalid `RRR_OLD_BUMP_VERSION`; bad subject parse + `drop_changelog_commit` can raise `Stalled` on `invalid version` instead of legacy fallback
- **Proposed resolution**: If bump subject does not yield a semver `old_version`, skip bullet staging and versioned changelog drop (legacy `replaces_version` path only)

### FINDING_8:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:88-90 (Deterministic pre-pass)
- **Concern**: `auto-generated` and `LARCH_BUMP_FILES` `--ours` are not bash parity. Scenario: Bash pre-pass only auto-resolves CHANGELOG, `.claude-plugin/plugin.json`, `version.go`, and `go.sum`; other paths (including `LARCH_BUMP_FILES`) go to vendor/waterfall — auto `--ours` can hide real conflicts
- **Proposed resolution**: Drop `auto-generated` unless tied to a named bash rule; do not `checkout_ours` `LARCH_BUMP_FILES` paths in the pre-pass (keep them for waterfall / `NeedsUserInput`)

### FINDING_9:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:56-69
- **Concern**: Re-bump tail always runs classify/apply/changelog with no bump_type NONE gate. Scenario: Bash skips apply_bump and ship_pr_commit_changelog_after_rebump when BUMP_TYPE=NONE; unconditional apply_bump can add a redundant Bump version commit and changelog work on no-op classifies
- **Proposed resolution**: Wrap steps 5–6 in bump_type != "NONE" and non-empty new_version (match scripts/ship-pr.sh ~3074–3087); stub a NONE path in test_rebase.py

### FINDING_10:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:88-91
- **Concern**: Pre-pass adds auto-generated and LARCH_BUMP_FILES checkout_ours not in bash run_rebase_rebump. Scenario: Bash only auto-resolves CHANGELOG paths and checkout --ours for plugin.json (path-guarded) version.go and go.sum; extra rules add scope and can mis-resolve paths bash would send to the fixer
- **Proposed resolution**: Limit the deterministic pre-pass to bash parity (CHANGELOG via changelog.auto_resolve; plugin.json / version.go / go.sum via checkout_ours); drop auto-generated and LARCH_BUMP_FILES unless a separate issue defines bump-commit detection

### FINDING_11:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:92-97
- **Concern**: _resolve_conflicts says to build a fixer prompt from conflict-resolution.md while also calling launch_*-ci. Scenario: Launch scripts already inject CONFLICT_CONTEXT and optional PLAN_CONTEXT; duplicating prompt assembly in rebase.py is extra surface and can drift from launch-cursor-ci.sh
- **Proposed resolution**: Have _resolve_conflicts only call agents.launch_tier / run_waterfall with role=resolve-conflict and conflict_files; delete prompt-building prose from the plan

### FINDING_12:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: correctness
- **Location**: plan.txt:101-103
- **Concern**: rebase --skip on empty/already-applied is named but not tied to continue failure signals. Scenario: rebase-push.sh continue failures return exit 3 with REBASE_ERROR text; blind skip can skip real failures (skills/implement/references/conflict-resolution.md ~110)
- **Proposed resolution**: After non-zero rebase_continue with no unmerged paths, skip only when combined stderr/stdout matches empty/already-applied patterns; otherwise Stalled; add a stub case in test_rebase.py

### FINDING_13:
- **Reviewer(s)**: Cursor-dyn-bash-parity
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/rebase.py (plan §_force_push_branch)
- **Concern**: Force-push parity cites `rebase-push.sh` PUSH_REMOTE/strict lease, but `run_rebase_rebump` pushes via `git-force-push.sh`. Scenario: Fork/topic branches: rebump always fetches/pushes `origin` with a plain `--force-with-lease` (no pinned OID, no `branch.*.pushRemote`), while the plan ports `rebase-push.sh` `PUSH_REMOTE` + one-shot `EXPECTED_REMOTE_OID` (`scripts/rebase-push.sh:272-287` vs `scripts/git-force-push.sh:85-114`, `scripts/ship-pr.sh:3114-3121`)
- **Proposed resolution**: Wire `_force_push_branch` to the rebump tail authority (`git-force-push.sh`) or document an intentional upgrade; if keeping `rebase-push.sh` semantics, add `PUSH_REMOTE` resolution and single OID lease there

### OOS_1:
- **Description**: `refresh-run-logs` and pre-drop `larch-logs/` fixup omitted (driver-owned). Scenario: Dirty tracked `larch-logs/` can make `drop_bump_commit` return `DROPPED=false` and `Stalled` before rebase — bash runs `refresh-run-logs.sh` and scoped fixup first
- **Reviewer**: Cursor-Edge
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: plan.txt:22-28 / Approach
- **Phase**: design

### OOS_2:
- **Description**: No `defer_push` / `HAS_BUMP` inputs. Scenario: Bash `run_rebase_rebump` skips push when `defer_push` and skips classify/apply when `HAS_BUMP=false`
- **Reviewer**: Cursor-Edge
- **Severity**: latent
- **Focus area**: correctness
- **Location**: plan.txt:18-20 (`rebase_and_rebump` API)
- **Phase**: design

### OOS_3:
- **Description**: Version-regression guard uses base_remote/base_ref but apply_bump still hardcodes origin/main. Scenario: Fork/upstream bases can disagree with apply_bump’s origin/main fetch and guards (python/version_bump.py ~566-578)
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: plan.txt:56-60
- **Phase**: design
