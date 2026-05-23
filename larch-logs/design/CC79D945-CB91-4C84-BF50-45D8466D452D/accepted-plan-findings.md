### FINDING_1: ci-wait transient bail uses kv BAIL_REASON from stdout not stderr capture in fai

- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ship-pr.sh:1776-1882
- **Concern**: ci-wait transient bail uses kv BAIL_REASON from stdout not stderr capture in fail_file
- **Scenario/breakage**: ci-wait.sh and merge-pr.sh can return rc=0 while stdout reports ACTION=bail or MERGE_RESULT=error/admin_failed with a transient error, so with_transient_retry returns immediately and the existing case path still exits 6 without the planned 3-attempt retry
- **Suggested fix**: Retry or gate on parsed ACTION/BAIL_REASON (or a small wrapper function around the parse branch), not the raw ci-wait invocation alone
- **Reviewer**: Codex-Edge, Cursor-Edge, Cursor-Pragmatic


### FINDING_10: run_checks_phase can exit_stall 6 when resolve_checks_log_path fails before lint

- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/ship-pr.sh:712-715,750-751
- **Concern**: run_checks_phase can exit_stall 6 when resolve_checks_log_path fails before lint loop; plan only wires waterfall before the post-loop stall
- **Scenario/breakage**: Checks stall from bad redacted log path never gets Cursor Codex Claude recovery despite same stall code
- **Suggested fix**: Decide whether that path should call run_recovery_waterfall or explicitly exclude it with rationale in ship-pr.md
- **Reviewer**: Cursor-Innovation, Cursor-Requirements


### FINDING_11: Plan points transient ci-wait wrap at outer ci-wait.sh call line 1776 while exit

- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/ship-pr.sh:1776-1883
- **Concern**: Plan points transient ci-wait wrap at outer ci-wait.sh call line 1776 while exit_transient_net fires at bail branch line 1882
- **Scenario/breakage**: Wrapper that only re-invokes ci-wait without enclosing bail classification never retries transient bails
- **Suggested fix**: Implement with_transient_retry around a helper that runs ci-wait and handles ACTION=bail transient signature in one retried unit
- **Reviewer**: Cursor-Innovation


### FINDING_12: Acceptance claims all existing test-ship-pr cases pass without modification alon

- **Severity**: nit
- **Focus area**: code-quality
- **Location**: plan.txt:195-196
- **Concern**: Acceptance claims all existing test-ship-pr cases pass without modification alongside large structural edits
- **Scenario/breakage**: Likely false without fixture or line-anchor updates
- **Suggested fix**: Relax wording to allow minimal harness edits or reserve budget for test maintenance
- **Reviewer**: Cursor-Innovation


### FINDING_13: Constraint H groups ship-pr-rrr-phase14 with no-op resume branches but current h

- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:138-140 vs scripts/ship-pr.sh:1996-2008
- **Concern**: Constraint H groups ship-pr-rrr-phase14 with no-op resume branches but current handler runs run_rebase_rebump and clears RESUME_PHASE
- **Scenario/breakage**: Implementer may delete run_rebase_rebump on resume and break scripts/test-ship-pr.sh phase14 and docs/linting.md expectations
- **Suggested fix**: Spell out retention of current ship-pr-rrr-phase14 behavior or an equivalent explicit re-entry path; reserve no-op wording for tokens that never needed run_rebase_rebump
- **Reviewer**: Cursor-Pragmatic, Cursor-Requirements


### FINDING_14: Planned git checkout and rm on path deltas without quoting discipline

- **Severity**: important
- **Focus area**: security
- **Location**: plan.txt:81-86
- **Concern**: Planned git checkout and rm on path deltas without quoting discipline
- **Scenario/breakage**: Word splitting or empty arg list could corrupt checkout scope
- **Suggested fix**: Use line-wise or array staging with empty guard and git checkout -- pathargs and rm -f -- pathargs
- **Reviewer**: Cursor-Pragmatic


### FINDING_15: Internal waterfall role tokens (checks-recover pr-prep-recover …) conflict with

- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:64-73 vs :7-9
- **Concern**: Internal waterfall role tokens (checks-recover pr-prep-recover …) conflict with launch-claude-ci.sh argv roles (recover-checks recover-pr-prep …) and with “claude_role preserves the original token end-to-end”
- **Scenario/breakage**: checks-recover/pr-prep-recover/pr-create-recover preserved end-to-end would be rejected by a launcher accepting recover-checks/recover-pr-prep/recover-pr-create
- **Suggested fix**: Add an explicit mapping table: run_recovery_waterfall role → vendor roles (fix resolve-conflict) → launch-claude-ci.sh --role value; reconcile the “preserve token” sentence with the public CLI names
- **Reviewer**: Codex-Requirements, Cursor-Requirements


### FINDING_16: Documents mandatory Phase 1–4 conflict-resolution.md after exit 5 when CALLER_KI

- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:1595-1596 vs plan “Wire waterfall” / exit 5 removal
- **Concern**: Documents mandatory Phase 1–4 conflict-resolution.md after exit 5 when CALLER_KIND=ship_pr_pre_push and resume via --resume-phase ship-pr-rrr-phase14
- **Scenario/breakage**: Removing exit 5 without updating SKILL and conflict-resolution prose leaves operators and automation following a dead handoff contract
- **Suggested fix**: Add paired doc updates (and any step2-implement routing if applicable) or explicitly scope “prompt-side contract change” with acceptance criteria
- **Reviewer**: Cursor-Requirements


### FINDING_18: New harness scripts/test-launch-claude-ci.sh is not listed for Makefile shard .P

- **Severity**: important
- **Focus area**: risk-integration
- **Location**: Makefile / agent-lint.toml / docs/linting.md vs plan files 11-14
- **Concern**: New harness scripts/test-launch-claude-ci.sh is not listed for Makefile shard .PHONY agent-lint harness registry or docs table
- **Scenario/breakage**: make lint or relevant-checks misses the new harness and allow-list regressions slip
- **Suggested fix**: Add Makefile target wire into a test-harnesses-N shard mirror test-launch-cursor-ci test-launch-codex-ci add agent-lint.toml paths and extend docs/linting.md
- **Reviewer**: Cursor-Requirements


### FINDING_19: with_transient_retry only retries non-zero command failures, but merge-pr.sh and

- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:102,127-134; scripts/merge-pr.sh:26-31; scripts/ci-wait.sh:34-42
- **Concern**: with_transient_retry only retries non-zero command failures, but merge-pr.sh and ci-wait.sh report transient failures in zero-exit KV envelopes
- **Scenario/breakage**: ci-wait.sh ACTION=bail and merge-pr.sh MERGE_RESULT=error/admin_failed will make with_transient_retry return immediately, so existing exit_transient_net still fires with no bounded retry
- **Suggested fix**: Add site-specific retry predicates or a callback mode that parses ACTION/BAIL_REASON and MERGE_RESULT/ERROR after each attempt before deciding success
- **Reviewer**: Codex-Arch, Codex-Pragmatic


### FINDING_2: Tier availability plan cites session-env CURSOR_PRESENT or CODEX_PRESENT; ship-p

- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/ship-pr.sh:1227-1235 vs plan tier gates
- **Concern**: Tier availability plan cites session-env CURSOR_PRESENT or CODEX_PRESENT; ship-pr today gates on command -v cursor only
- **Scenario/breakage**: Session can mark CURSOR_PRESENT=false while cursor exists; waterfall would skip tier A but existing CI-fix path would still launch Cursor, changing recovery behavior and tests
- **Suggested fix**: Match one policy: either teach run_ci_fix_vendor to honor session-env booleans or document that waterfall uses command -v only like today
- **Reviewer**: Cursor-Edge, Cursor-Innovation, Cursor-Pragmatic


### FINDING_20: Claude waterfall role mapping preserves resolve-conflict-nonbump, but launch-cla

- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:65-73,146-160
- **Concern**: Claude waterfall role mapping preserves resolve-conflict-nonbump, but launch-claude-ci argv/tests accept resolve-conflict
- **Scenario/breakage**: The Claude tier for non-bump conflict recovery is rejected as an invalid role or remains untested
- **Suggested fix**: Normalize the Claude role to resolve-conflict or add resolve-conflict-nonbump to launcher validation, docs, prompts, and tests
- **Reviewer**: Codex-Arch


### FINDING_21: Waterfall takes a fail_file but Cursor/Codex launcher prompts receive no local f

- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:64-88,122-125; scripts/launch-cursor-ci.sh:111-120; scripts/launch-codex-ci.sh:95-104
- **Concern**: Waterfall takes a fail_file but Cursor/Codex launcher prompts receive no local failure log for pr-prep and pr-create recovery
- **Scenario/breakage**: OOS disposition or PR-create failures launch agents told only "Failed run id"; there may be no failed CI run and no actionable error context
- **Suggested fix**: Promote --failure-log and explicit recover-pr-prep/recover-pr-create roles to Cursor and Codex too, or add a generic recovery launcher that receives phase, failure log, and verify command
- **Reviewer**: Codex-Arch, Codex-Innovation


### FINDING_22: Source-safety plan gates only bottom dispatch while existing top-level argument

- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:142-144; scripts/ship-pr.sh:141-357,1988-2034
- **Concern**: Source-safety plan gates only bottom dispatch while existing top-level argument parsing, state initialization, validation, and resume handling run before the loop
- **Scenario/breakage**: source scripts/ship-pr.sh with no args still exits via --state-file required; with caller args it can consume args or write state, so source_safety_no_side_effects_when_sourced cannot pass
- **Suggested fix**: Move argv parsing, required-arg validation, initial state creation, resume handling, and the main loop under the BASH_SOURCE main guard; leave only constants and function definitions at source time
- **Reviewer**: Codex-Arch, Codex-Edge, Codex-Innovation, Codex-Pragmatic


### FINDING_23: Rollback is specified as git checkout -- $tracked_delta and rm -f $untracked_del

- **Severity**: important
- **Focus area**: security
- **Location**: plan.txt:81-86
- **Concern**: Rollback is specified as git checkout -- $tracked_delta and rm -f $untracked_delta with word-expanded paths
- **Scenario/breakage**: Consumer repo paths containing spaces, globs, or leading dashes can be split or interpreted incorrectly, reverting or deleting the wrong files
- **Suggested fix**: Process delta files with while IFS= read -r path loops and quoted -- "$path" arguments, or use a shared pathspec-file helper
- **Reviewer**: Codex-Arch


### FINDING_26: Waterfall rollback baseline ignores staged/index-only changes

- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ship-pr.sh:50-55,1216-1307
- **Concern**: Waterfall rollback baseline ignores staged/index-only changes
- **Scenario/breakage**: A tier can git add a new or modified file, fail verification, then rollback sees no tracked delta because capture_tracked_dirty_paths only uses git diff against the worktree; stale staged changes can leak into the next tier or final commit
- **Suggested fix**: Use the lint-fix-loop pattern that unions git diff --name-only and git diff --name-only --cached, and rollback with git reset HEAD -- path before git checkout -- path
- **Reviewer**: Codex-Edge


### FINDING_27: Rebase conflict waterfall has contradictory verification contract

- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/ship-pr.sh:1429-1439,1695-1738
- **Concern**: Rebase conflict waterfall has contradictory verification contract
- **Scenario/breakage**: A shared run_recovery_waterfall verifier that runs relevant checks for resolve-conflict-nonbump can run while a rebase is still unresolved or treat unrelated checks as proof, while the later plan text requires git rebase --continue plus _run_rebase_rebump_verify_plain_no_push
- **Suggested fix**: Split rebase-conflict recovery into a role-specific verifier callback: launch tier, assert HEAD, continue rebase, then run _run_rebase_rebump_verify_plain_no_push
- **Reviewer**: Codex-Edge


### FINDING_28: New --failure-log prompt input lacks a validation/redaction test contract

- **Severity**: latent
- **Focus area**: security
- **Location**: scripts/launch-claude-ci.sh (planned)
- **Concern**: New --failure-log prompt input lacks a validation/redaction test contract
- **Scenario/breakage**: The new write-capable Claude launcher accepts --failure-log, but the listed tests do not constrain it; an accidental or hostile absolute path could be read into the Claude prompt/output instead of a session failure log
- **Suggested fix**: Require provided failure logs to be canonical regular non-symlink files under IMPLEMENT_TMPDIR/session roots, cap size, redact before prompt insertion, and add unsafe path/symlink tests
- **Reviewer**: Codex-Edge, Codex-Pragmatic


### FINDING_29: PR-create recovery verifies with push/PR dry-run instead of the helper that actu

- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:75-78
- **Concern**: PR-create recovery verifies with push/PR dry-run instead of the helper that actually failed
- **Scenario/breakage**: Pre-PR write-final-report can be broken while git push --dry-run passes, causing the waterfall to accept an unfixed tier and skip later tiers
- **Suggested fix**: Make site-specific verification re-run the failing helper before declaring tier success; use dry-run push only as an additional probe
- **Reviewer**: Codex-Innovation


### FINDING_3: Source-safe guard moves only the main while-loop (2013-2034) per plan; RESUME_PH

- **Severity**: latent
- **Focus area**: architecture
- **Location**: scripts/ship-pr.sh:1988-2034
- **Concern**: Source-safe guard moves only the main while-loop (2013-2034) per plan; RESUME_PHASE preambles stay above it
- **Scenario/breakage**: RESUME_PHASE handler and all earlier entry logic still run when sourced; resume can advance phases or call run_rebase_rebump while tests expect pure library load
- **Suggested fix**: Extend the guard spec to cover all top-level entry after function definitions or relocate argv and state bootstrap inside the same main guard
- **Reviewer**: Cursor-Edge, Cursor-Innovation, Cursor-Pragmatic


### FINDING_30: Transient retry plan says stderr-only capture, but current transient detection i

- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ship-pr.sh:1128-1132
- **Concern**: Transient retry plan says stderr-only capture, but current transient detection intentionally classifies combined stderr and stdout
- **Scenario/breakage**: Helpers that emit transport failures on stdout stop being retried and fall back to the old transient bail path
- **Suggested fix**: Have with_transient_retry classify combined stdout+stderr in memory while only appending redacted diagnostics to fail_file
- **Reviewer**: Codex-Innovation


### FINDING_31: Plan treats --allow-root as Claude write/tool permission, but the existing subpr

- **Severity**: important
- **Focus area**: architecture
- **Location**: scripts/launch-claude-subprocess.sh:96-119
- **Concern**: Plan treats --allow-root as Claude write/tool permission, but the existing subprocess uses it only for local path validation
- **Scenario/breakage**: Claude CI tier may be implemented with a writer prompt but no real tool-permission wiring, yielding a tier that cannot edit or has broader access than intended
- **Suggested fix**: Specify and test the actual Claude CLI permission mechanism separately from context-root validation; add argv/meta tests that prove Edit/Write/Bash are scoped to repo root
- **Reviewer**: Codex-Innovation


### FINDING_32: Claude recovery role names are inconsistent between waterfall input and launcher

- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:64-73
- **Concern**: Claude recovery role names are inconsistent between waterfall input and launcher argv
- **Scenario/breakage**: run_recovery_waterfall preserves checks-recover/pr-prep-recover/pr-create-recover for Claude, but launch-claude-ci.sh is specified to accept recover-checks/recover-pr-prep/recover-pr-create, causing the Claude tier to fail validation
- **Suggested fix**: Map waterfall roles to the launcher enum or use one canonical enum everywhere; add a test for the actual tier-3 argv
- **Reviewer**: Codex-Pragmatic


### FINDING_4: Second same-version/version-regression occurrence lacks persisted counter semant

- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt Detail _run_step8_same_version_mechanical
- **Concern**: Second same-version/version-regression occurrence lacks persisted counter semantics
- **Scenario/breakage**: Implementer may use ephemeral shell state and never reach exit_stall 8 on true repeat, or stall too early
- **Suggested fix**: Specify a RESUME_PHASE or CALLER_KIND keyed counter in state-file with clear increment and reset rules
- **Reviewer**: Cursor-Edge


### FINDING_5: Classifier inputs today mix stderr file plus appended stdout (e.g. create-pr) wh

- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt Edge cases Secret leakage bullet for with_transient_retry
- **Concern**: Classifier inputs today mix stderr file plus appended stdout (e.g. create-pr) while bullet says stderr-only
- **Scenario/breakage**: If helper only inspects stderr, transient strings that land only on stdout never retry and silently change stall vs bail behavior
- **Suggested fix**: Define one classification input per site (mirror existing cat fail_file patterns) and drop the stderr-only claim unless enforced everywhere
- **Reviewer**: Cursor-Edge


### FINDING_6: Waterfall called only before the final exit_stall 6 path

- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ship-pr.sh:712-715
- **Concern**: Waterfall called only before the final exit_stall 6 path
- **Scenario/breakage**: resolve_checks_log_path failure still exit_stalls 6 with no vendor attempt though logs may be recoverable once tmp paths settle
- **Suggested fix**: Including that branch in checks-recover waterfall or explicitly documenting intentional no-waterfall fast-fail
- **Reviewer**: Cursor-Edge, Cursor-Pragmatic


### FINDING_7: Planned rollback is git checkout and rm on path deltas; lint-fix-loop uses forbi

- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: plan.txt run_recovery_waterfall rollback vs scripts/lint-fix-loop.sh:99-135
- **Concern**: Planned rollback is git checkout and rm on path deltas; lint-fix-loop uses forbidden-path aware post_dispatch_forbidden_revert
- **Scenario/breakage**: forbidden-path logic also walks submodule paths from .gitmodules; tier rollback may leave submodule dirt that next tier treats as success
- **Suggested fix**: Use NUL-delimited path streams with validation, git restore --pathspec-from-file=- --pathspec-file-nul for tracked paths, and portable xargs -0 git clean -f -- for new untracked paths
- **Reviewer**: Codex-Innovation, Cursor-Edge, Cursor-Innovation


### FINDING_8: Plan names RESUME_PHASE branches for step8_apply_bump_same_version but code sets

- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ship-pr.sh:903-904,1989-1990
- **Concern**: Plan names RESUME_PHASE branches for step8_apply_bump_same_version but code sets RESUME_PHASE=bump and CALLER_KIND=step8_apply_bump_same_version
- **Scenario/breakage**: Current same-version state is RESUME_PHASE=bump plus CALLER_KIND=step8_apply_bump_same_version, so implementer may add the wrong no-op branch
- **Suggested fix**: Describe legacy compatibility as RESUME_PHASE=bump with CALLER_KIND=step8_apply_bump_same_version (and parallel for step8b_rebase force-push-gate) matching scripts/ship-pr.sh:1988-2010
- **Reviewer**: Codex-Requirements, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements


### FINDING_9: Plan replaces Phase 14 exit 5 with in-script Cursor then Codex then Claude water

- **Severity**: important
- **Focus area**: architecture
- **Location**: scripts/ship-pr.sh:1695-1707
- **Concern**: Plan replaces Phase 14 exit 5 with in-script Cursor then Codex then Claude waterfall
- **Scenario/breakage**: Loses explicit handoff to skills/implement conflict-resolution Phase 1-4 aggregator unless another path still emits it
- **Suggested fix**: Confirm with maintainers that autonomous repair is intended; if not, keep a bail tier or emit_kv-only handoff after exhaustion
- **Reviewer**: Cursor-Innovation


