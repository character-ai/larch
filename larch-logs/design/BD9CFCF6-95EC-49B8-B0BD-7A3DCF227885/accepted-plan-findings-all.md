### FINDING_1: Step 5 lint-fix loop must commit after successful recheck when lint-fix ever applied
- **Reviewer(s)**: Cursor-Arch, Cursor-dyn-review-loop-commit
- **Severity**: important
- **Concern**: `_step5_post_round_gates` can exit the lint-fix loop via multiple successful `break` paths (cap success, normal recheck pass, non-fail recheck) without committing working-tree edits from prior `applied` iterations. If any earlier pass returned `applied` and a later pass returns `no-changes` before recheck passes, the round can return `complete` while porcelain stays dirty, reproducing the ship-driver dirty-tree stall (#4712).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Track `lint_fix_applied` across the loop; before each successful `break`, call `_commit_review_loop_dirty_tree` when the flag is true; stall with `lint-fix-commit-failed` if commit fails
  - From Cursor-dyn-review-loop-commit: In `_step5_post_round_gates`, use `lint_applied_ever |= (lint_status == "applied")` and call `_commit_review_loop_dirty_tree` only when `lint_applied_ever` and recheck passes/skips


### FINDING_2: Lint-fix commit must not sweep pre-existing dirty paths via `git add -A`
- **Reviewer(s)**: Codex-dyn-review-loop-commit
- **Severity**: important
- **Concern**: A Step 5 lint-fix commit helper that stages the full dirty tree can include unrelated pre-existing unstaged paths present at lint-fix entry, not just lint-fix deltas. That widens the commit scope and can hide concurrent working-tree pollution.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-review-loop-commit: Carry the lint-fix delta or assert a clean pre-lint baseline, then stage only verified lint-fix paths or stall before commit


### FINDING_4: Partition self-heal must not treat an already-fixed cleanup selector as unfixed
- **Reviewer(s)**: Cursor-dyn-ci-harness-contracts
- **Severity**: blocking
- **Concern**: Naive matching on `-k cleanup` can also match Makefile recipes already narrowed to `-k 'cleanup and not cleanup_target_ok'` (e.g. line 788). A stale overlap log could rewrite an already-correct `test-implement-cleanup-script` recipe and break strict-partition or pytest selection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-ci-harness-contracts: Parse only the `test-implement-cleanup-script` recipe; treat unfixed only when `-k` expression is exactly `cleanup` (no `not cleanup_target_ok`); no-op otherwise


### FINDING_5: Partition self-heal must preserve Makefile tab-indented recipes
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: Makefile recipe lines require literal tab indentation. A mechanical rewrite of the `test-implement-cleanup-script` line using spaces can make `make` fail, causing local verify to fail and roll back an otherwise useful fix.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Augment `_apply_finalize_cleanup_partition_fix` constraints: detect the target recipe line, rewrite in place, and assert the line still begins with a literal tab


### FINDING_6: Legacy-prefix ALLOW self-heal must use a safe insertion anchor and shell-safe path entries
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Codex-Pragmatic
- **Severity**: important
- **Concern**: The legacy-prefix allow-list self-heal underspecifies both where to insert into `ALLOW=(` and how to validate path tokens. A bad insertion can break `scripts/test-legacy-title-prefix-literals-scope.sh` bash syntax; an unquoted or metacharacter-bearing log-derived path can be evaluated when the harness reruns.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Require append of a new quoted path entry immediately before the closing `)` of the existing `ALLOW=(` block, sorted optional, skip if already present
  - From Codex-Arch: Reject paths outside a strict safe repo-path regex before editing ALLOW, or write properly shell-quoted array entries.
  - From Codex-Pragmatic: Reject allow-list paths outside the existing safe bare-token shape, for example ^[A-Za-z0-9._/-]+$, or write entries with robust Bash single-quoting before local verify.


### FINDING_7: Known harness prepass must apply all matching fixes before local verify
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Concern**: If one CI run contains both legacy-prefix and cleanup-partition failures, short-circuiting after the first known fix leaves the second failure in place. Local verify then fails and rolls back the useful first fix.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Define _apply_known_harness_fix to run both narrow helpers, collect whether any changed files, and verify once after all matching known fixes are applied.


### FINDING_8: CI auto-fix must skip agent launcher when mechanical harness fix applies
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: `_run_cycle` currently always invokes `agents.launch_tier` after baseline capture. When `_apply_known_harness_fix` matches, running the agent burns tokens/time and risks head-changed rollback of the mechanical edit before push.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: In CI auto-fix, a matched signature still invokes `agents.launch_tier`, burning tokens/time and risking rollback of the mechanical edit before push Restructure `_run_cycle`: after baseline capture, if `_apply_known_harness_fix` returns true set `fix_attempted=true` and branch directly to the existing forbidden-path/verify/delta/stage_and_push block; skip `agents.launch_tier` and the post-agent head-changed guard entirely on that branch


### FINDING_9: Register `lint-fix-commit-failed` in Step 5 stall taxonomy
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-dyn-review-loop-commit
- **Severity**: important
- **Concern**: The plan adds a `lint-fix-commit-failed` stall token but `step5-review-branches.md` only lists `lint-fix-failed`, `lint-fix-attempt-cap`, and `lint-fix-main-agent-required` as durable lint-fix bail tokens. The new token would seed empty `BAIL_REASON` in `ship-pr-state.sh` and weaken Step 18a recovery/logging.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add ### UPDATED: skills/implement/references/step5-review-branches.md: include lint-fix-commit-failed in Tool Failures stall list and lint-fix bail token set alongside lint-fix-failed and lint-fix-attempt-cap
  - From Cursor-dyn-review-loop-commit: Add `### UPDATED: skills/implement/references/step5-review-branches.md`: include `lint-fix-commit-failed` in the lint-fix stall token list and Tool Failures logging bucket


### FINDING_10: `step-5-resume.sh` must fail-closed on `commit-fixes` failure
- **Reviewer(s)**: Cursor-dyn-review-loop-commit
- **Severity**: important
- **Concern**: MAV/handoff commit uses `commit-fixes --stage-all || true` and ignores failures. Main-agent review fixes can stay dirty after a failed commit; the loop resumes and ship later hits `push.assert_clean_worktree` (the #4712 stall class).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-review-loop-commit: Add `### UPDATED: skills/implement/scripts/step-5-resume.sh`: drop `|| true`, parse `COMMITTED=` / `ERROR=`, and stall (or exit non-zero) when commit fails while porcelain is non-empty; mirror `implement_dispatch.py:451-452` fail-closed behavior


### FINDING_11: Structure test must pin Step 7 `commit-fixes --stage-all`, not only self-review
- **Reviewer(s)**: Cursor-Requirements, Cursor-dyn-review-loop-commit
- **Severity**: important
- **Concern**: Gap #3 backup depends on Step 7 using `--stage-all`, but `test-implement-structure.sh` jumps from Step 6 checks to `step-7a` without a Step-7 launcher pin. Line 96 only requires `commit-fixes --stage-all` somewhere in `SKILL.md`, which Step 5 resume already satisfies, while Step 7 still uses `<specific-files>` at line 695. Updating prose alone is a no-op for the harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add a Step-7-specific assertion: include `python/cli.py review-and-fix commit-fixes --stage-all` in the launcher list between Step 6 and step-7a and add `forbid(skill, 'commit-fixes <specific-files>', 'Step 7 must stage all review fixes')` or an equivalent Step-7-scoped pin; replace the plan wording "update pinned Step 7 expectation from `<specific-files>`" because no such pin exists today
  - From Cursor-dyn-review-loop-commit: Replace the plan’s structure-test bullet with `forbid(skill, 'review-and-fix commit-fixes <specific-files>')` or `require_near` under `## Step 7 — Second Commit` for `commit-fixes --stage-all`


### FINDING_12:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: security
- **Location**: plan.txt:8,76-80,101-104; python/ci_agentic_fix.py planned; python/test_ci_agentic_fix.py planned
- **Concern**: [SCOPE-REDUCTION] Legacy-prefix self-heal can auto-expand ALLOW for any reported repo path. Scenario: The plan says not to weaken the legacy-prefix guard, but the proposed helper parses an arbitrary unexpected path and adds it to ALLOW when the file exists and contains the literal. A future PR could introduce a new sprawl path and have CI self-approve it, bypassing the anti-sprawl review contract.
- **Proposed resolution**: Restrict the mechanical fix to the known omitted path from this incident, python/preflight.py, or a tiny hard-coded known-path allow set. For any other unexpected path, return False and delegate to the existing Claude fixer. Update tests to assert other paths are not auto-allowlisted.


### FINDING_13:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/review_and_fix.py:1124-1186, python/checks.py:2108-2145
- **Concern**: [SCOPE-REDUCTION] Planned Step 5 dirty-tree commit helper duplicates existing lint-fix commit handling and widens the commit surface. Scenario: checks.run_lint_fix already commits Step 5 lint fixes when it starts from a clean tree, and Step 7 --stage-all covers later prompt-side/manual review edits before ship. The new helper only materially changes non-clean-baseline cases, where git add -A can fold unrelated dirty files into a lint-fix commit before the normal Step 6/7 boundary.
- **Proposed resolution**: Drop the new Step 5 commit helper and its tests. Keep the Step 7 --stage-all change; if a Step 5 fallback remains necessary, commit only the delta_paths returned by checks.run_lint_fix and do not run git add -A on the whole tree.


### FINDING_14:
- **Reviewer(s)**: Codex-dyn-ci-harness-contracts
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: <TMPDIR>/plan.txt:7-9,74-80; scripts/test-legacy-title-prefix-literals-scope.sh:11-24,41-45
- **Concern**: [SCOPE-REDUCTION] Legacy-prefix self-heal can auto-allow any reported path. Scenario: The current guard makes ALLOW the explicit anti-sprawl contract and tells authors to extend it only when deliberate. The plan parses any unexpected path, checks only that the file exists and still contains the literal, then inserts it into ALLOW. A future accidental [PLANNED] or [IN PROGRESS] literal would be blessed by CI instead of blocked.
- **Proposed resolution**: Limit the mechanical fix to the exact known incident signature/path, or skip mechanical ALLOW edits for arbitrary unexpected paths and fall back to the delegated fixer/manual review path.




### FINDING_1: lint-fix-commit-failed missing from durable bail-token allowlists
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Requirements
- **Severity**: important
- **Concern**: The plan introduces `lint-fix-commit-failed` as a Step 5 stall reason but does not fully wire it into every durable bail-token surface. If the token is added only to the Tool Failures prose list in `step5-review-branches.md` without updating the inline three-token durable-bail predicate, `BAIL_REASON` stays empty for those stalls. The same gap exists if `python/config.py` `LINT_FIX_BAIL_REASON_TOKENS` (documented SSOT for `STALL_RECOVERY_BAIL_REASON_TOKENS`, `stall_recovery` lint-fix-bail-token classification, and related tests) is not updated. Step 18a stall classification then may not see the lint-fix commit failure token.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Expand FINDING_9 to also add lint-fix-commit-failed to the explicit bail-token enumeration in the compute durable lint-fix bail value sentence (or replace the closed three-token list with the full durable set).
  - From Cursor-Innovation: Update the explicit The lint-fix stall tokens are ... sentence and the durable-bail predicate to include lint-fix-commit-failed alongside lint-fix-failed lint-fix-attempt-cap lint-fix-main-agent-required
  - From Cursor-Requirements: Add ### UPDATED: python/config.py to append lint-fix-commit-failed to LINT_FIX_BAIL_REASON_TOKENS; extend python/test_stall_recovery.py _LINT_FIX_BAIL_TOKENS (or derive from config) so allowlist/classifier tests cover the new token


### FINDING_2: lint-fix delta commit may bundle unrelated staged hunks
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The proposed `_commit_lint_fix_delta_paths` stages paths then calls `git-commit.sh -m` without `--only`. `git-commit.sh` commits whatever is already staged when no path args are passed; a dirty index from earlier review work can bundle unrelated hunks into the lint-fix commit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Mirror `_stage_and_commit_round`: write a pathspec file, `git add --pathspec-from-file`, then `git-commit.sh --only --pathspec-from-file ... -m`


### FINDING_3: mechanical CI prepass may skip delegate on partial fix
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: Mechanical CI prepass skips the existing Claude delegate whenever any known fix applies. A CI run with one known harness failure plus another unrelated fixable failure will apply the known edit, skip `agents.launch_tier`, fail local verify on the unrelated job, roll back, and repeat until `ci-fix-exhausted` instead of using the existing fixer path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Only bypass agents.launch_tier after the mechanical fix verifies all fixable failed jobs, or on mechanical verify failure roll back and fall through to the existing delegate path in the same cycle; add a focused mixed-known-plus-unrelated test



### FINDING_1: Step 5 resume handoff lacks orchestrator stall wiring on commit failure
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan makes `step-5-resume.sh` fail-closed on handoff commit failure (dropping `|| true` from `review-and-fix commit-fixes`), but `skills/implement/SKILL.md` has no branch after the `--ready-to-commit` background fence. Anti-halt text tells the orchestrator to continue after Bash completion, and lines 647+ assume resume succeeded. On MAV or `coder-main-agent-required` paths, a non-zero `--ready-to-commit` exit (or uncommitted review fixes) can still advance toward Step 6/8, reproducing the #4712 dirty-tree ship stall.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add an explicit SKILL.md branch: on non-zero exit from step-5-resume.sh --ready-to-commit, log the failure, set STALL_TRACKING=true with a durable bail token (new or existing), and skip to Step 16 before Step 6
  - From Cursor-Pragmatic: Add `### UPDATED: skills/implement/SKILL.md` (MAV/coder handoff section): after the `--ready-to-commit` notification, require non-zero exit or `COMMITTED=false` with dirty porcelain → log Tool Failures, set `STALL_TRACKING=true`, seed durable bail (new token or documented reuse), skip to Step 16; do not proceed to Step 6. Sync `skills/implement/scripts/step-5-resume.md` per its edit-in-sync rule.




### FINDING_1: Post-loop lint commit misses in-place edits on pre-dirty tracked files
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: Post-loop lint commit relies on unioned `FixOutcome.delta_paths` only, but `checks._delta_paths_after_dispatch` omits in-place edits to files already present in the `run_lint_fix` baseline tracked/untracked sets. On a non-clean pre-lint tree, lint-fix can modify already-dirty tracked files while `delta_paths` stays empty for those paths; `_commit_lint_fix_delta_paths` then commits nothing for them, porcelain remains dirty, and `push.assert_clean_worktree` can still fire at Step 8 despite the #3 fix.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Snapshot pre-lint HEAD plus porcelain at loop entry; on successful break commit paths changed since that snapshot (or intersect lint union with git diff --name-only against the snapshot), not delta_paths alone; add a regression test with a pre-dirty tracked file modified by lint-fix


### FINDING_2: Resume wrapper swallows commit-fixes KV stdout needed for fail-closed orchestrator parsing
- **Reviewer(s)**: Cursor-Innovation, Cursor-Requirements
- **Severity**: important
- **Concern**: `step-5-resume.sh` must relay `commit-fixes` KV stdout for orchestrator parsing after the `--ready-to-commit` background fence. The wrapper currently runs `commit-fixes` with `|| true` and does not guarantee `COMMITTED=` / `ERROR=` / `SHA=` lines appear on wrapper stdout, so the orchestrator cannot fail-closed on handoff commit failure, `resume-handoff-commit-failed` logging, or ship-pr-state seeding per Plan Section B.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Capture commit-fixes stdout, print COMMITTED=/ERROR=/SHA= lines unchanged, exit non-zero before review-and-fix step5 when COMMITTED=false and porcelain is non-empty
  - From Cursor-Requirements: Run commit-fixes --stage-all without redirecting stdout (rely on set -e for non-zero exit), or explicitly re-print COMMITTED=/ERROR=/SHA= to wrapper stdout before any early exit; document that orchestrator parsing depends on those lines appearing in the wrapper stream


### FINDING_3: Section B misclassifies Step 5 stall as resume-handoff commit failure
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: Plan Section B treats any non-zero `step-5-resume.sh --ready-to-commit` exit as `resume-handoff-commit-failed`. After a successful handoff commit, the wrapper still runs `review-and-fix step5` in the same script; a normal Step 5 stall (for example `lint-fix-failed`) exits non-zero with `STEP5_REVIEW_STATUS=stall` in stdout. Section B's blanket non-zero branch would misclassify that as a commit handoff failure, seed the wrong durable bail token, and skip to Step 16 without parsing the Step 5 envelope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Narrow the failure branch: use `resume-handoff-commit-failed` only when the commit phase fails (`COMMITTED=false` with dirty porcelain, or commit-phase `ERROR=` before step5 runs). When stdout contains `STEP5_REVIEW_STATUS=`, branch on that envelope instead; reserve the resume-handoff token for commit failures only. Document in `step-5-resume.md` that the wrapper must exit before `review-and-fix step5` on commit failure so exit code semantics stay separable




### FINDING_1: `step-5-resume.sh` aborts on clean-tree `commit-fixes` under `set -e`
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: blocking
- **Concern**: Removing `|| true` without an errexit-safe wrapper leaves `set -euo pipefail` aborting the script when `review-and-fix commit-fixes --stage-all` exits non-zero on a clean tree (empty porcelain after `git add -A`). The wrapper never reaches `review-and-fix step5`, so MAV/coder resume breaks on the common no-op handoff even though clean-tree `COMMITTED=false` should be treated as success.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Capture commit-fixes stdout/rc explicitly (disable errexit for that call); re-emit `COMMITTED=`/`ERROR=`/`SHA=`; if porcelain is empty after the call, continue to `step5` regardless of rc; exit non-zero only when porcelain remains dirty and commit failed
  - From Cursor-Pragmatic: In `step-5-resume.sh`, capture commit-fixes rc without aborting (subshell or `set +e` block), relay KV stdout, then branch: exit non-zero only when porcelain is non-empty after `COMMITTED=false`; otherwise continue to `step5`. Optionally add a matching clean-tree no-op in `commit_fixes` (exit 0, `COMMITTED=false`) and pin it in tests


### FINDING_2: Pre-lint snapshot cannot exclude unchanged pre-dirty paths from commit
- **Reviewer(s)**: Cursor-Innovation, Cursor-Requirements, Codex-Generic
- **Severity**: important
- **Concern**: The proposed lint-fix commit snapshot machinery cannot reliably distinguish files that were dirty before lint-fix from files actually changed by lint-fix. HEAD-plus-porcelain or an underspecified porcelain union can stage unrelated pre-existing edits, miss in-place edits, or recreate the #4712 ship dirty-tree stall by committing out-of-scope hunks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Mirror pre-coder snapshot machinery: capture per-path wt/index patches at lint-loop entry and commit only paths whose diffs diverge from those snapshots (reuse _path_matches_pre_coder_snapshot logic)
  - From Cursor-Requirements: Define commit candidates as paths in delta_paths union (git diff --name-only pre_lint_head) only; drop or tighten the vague porcelain-diff bullet so it cannot include files outside that union
  - From Codex-Generic: Revise the plan to snapshot pre-lint tracked dirty content, for example reuse the existing pre-coder per-path diff snapshot pattern, then compare after lint-fix and stage only paths whose pre-lint diff changed; add the two-pre-dirty-files test so only the lint-touched path is committed


### FINDING_3: Step 7 `--stage-all` still stages entire working tree
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: `commit_fixes --stage-all` still uses `git add -A` plus a bare commit. Unrelated staged or dirty files at Step 7 can ride into the review-fix commit despite pathspec-only lint-fix goals.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Change commit_fixes --stage-all to stage via pathspec-from-file built from review deltas only, matching _stage_and_commit_round



