### FINDING_1:
- **Reviewer(s)**: Cursor-Arch, Cursor-Edge
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: <TMPDIR>/plan.txt:161-167
- **Concern**: Deferred-to-E1 table omits check-remote-branch.sh even though ship-pr still reaches it live via implement-finalize.sh. Scenario: Plan defers deletion unless implement-finalize is repointed (line 167) but implement-finalize.sh is not in Files to modify; only python/finalize.py is. Under LARCH_SHIP_PR_IMPL=bash, premature manifest append/deletion of check-remote-branch.sh breaks Step 8b postbump remote probe
- **Proposed resolution**: Add check-remote-branch.sh to Deferred-to-E1 explicitly; note implement-finalize.sh stays bash until E1; gate deletion on zero live callers including $SCRIPT_DIR/check-remote-branch.sh from implement-finalize.sh

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-implement-rebase-macro.sh:154-176
- **Concern**: Structural harness still hard-pins deleted bash wrapper internals. Scenario: Plan line 159 says retarget pins to cli.py forms, but section (H) greps rebase-checkpoint-probe.sh for rebase_args and a single rebase-push.sh call. After B1 deletes the wrapper, make lint fails even if SKILL.md/step-7a cutover is correct
- **Proposed resolution**: Rewrite section (H) (and WRAPPER existence checks) to validate push checkpoint-probe CLI contract and SKILL.md/step-7a invocations; drop assertions on bash-only wrapper contents

### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:110-117
- **Concern**: git count-commits CLI contract underspecified for verify-skill-called.sh side channel. Scenario: verify-skill-called.sh sets COUNT_COMMITS_STATUS_FILE before sourcing lib-count-commits.sh (scripts/verify-skill-called.sh:240-244). Mapping table mentions status-file (line 54) but NEW git_cli.py section does not pin the env var name or always-exit-0 behavior
- **Proposed resolution**: Spell out in git_cli/git.py: honor COUNT_COMMITS_STATUS_FILE exactly, write ok|missing_main_ref|git_error, raw integer stdout, exit 0; update verify-skill-called.sh to invoke CLI with the same env var pattern

### FINDING_4:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: <TMPDIR>/plan.txt:144-145
- **Concern**: public remote_branch_state must not regress finalize postbump semantics. Scenario: Plan replaces finalize._remote_branch_state with public git.remote_branch_state while adding full KV/redacted ERROR parity for check-remote-branch.sh. Prior reviews flagged ls-remote vs stale local-ref and ERROR redaction gaps
- **Proposed resolution**: A single typed helper with two surfaces: trichotomy for finalize.postbump; emit_kv STATE/RC/ERROR (redacted) for git check-remote-branch CLI; port test-implement-finalize.sh / finalize parity tests for both

### FINDING_5:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: <TMPDIR>/plan.txt:113-114; scripts/lib-phantom-probe.sh:17-33,76-103
- **Concern**: [SCOPE-REDUCTION] Phantom plan permits porting append-execution-issue logic in B1. Scenario: The absorbed surface is phantom probing; current library delegates all execution-issue writes to append-execution-issue.sh. Porting that helper duplicates a security-sensitive markdown mutation path and expands B1 beyond the listed git/gh/ci primitives.
- **Proposed resolution**: Make probe_with_warn call existing scripts/append-execution-issue.sh via proc only; remove the "or ports it byte-identically" option and leave append-execution-issue.sh out of B1.

### FINDING_6:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:85; scripts/gh-run-logs.sh:41-55; scripts/gh-run-logs.md:3-9
- **Concern**: [SCOPE-REDUCTION] gh run-logs adds redaction to a raw stdout contract. Scenario: Legacy gh-run-logs emits the pointer plus the raw last 100 lines and existing callers perform redaction where needed. Moving redaction into the migrated verb changes diagnostic output and can hide data before caller-owned processing.
- **Proposed resolution**: Keep gh run-logs parity to pointer header plus unredacted tail-100 and exits 0/1/3; keep redaction at existing downstream pipes/callers.

### FINDING_7:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: architecture
- **Location**: <TMPDIR>/plan.txt:113-114; scripts/append-execution-issue.sh:76-155
- **Concern**: [SCOPE-REDUCTION] The plan allows porting append-execution-issue.sh inside the phantom work even though B1 only absorbs lib-phantom-probe.sh and phantom-probe-with-warn.sh. Scenario: Porting the append helper expands the PR into an unrelated lock/atomic-write migration; a partial reimplementation can corrupt execution-issues.md or lose concurrent warning entries
- **Proposed resolution**: Remove the "or ports it byte-identically" option and require phantom.probe_with_warn to call the existing scripts/append-execution-issue.sh helper; defer that helper's Python migration to a separate issue

### FINDING_8:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/cli.py:14-18
- **Concern**: [SCOPE-REDUCTION] Plan mandates six new *_cli.py companions plus matching test_*_cli.py files. Scenario: docs/python-migration.md registers (domain, verb) → (module, main) directly; only report_tokens_cli.py is a multi-step CLI pipeline. Six thin argparse wrappers duplicate the dispatcher pattern and add ~12 files without changing runtime behavior
- **Proposed resolution**: Register one main(argv) per domain module (git, push, pr, gh, merge, ci_monitor) with internal subcommand dispatch; keep library logic in the typed modules and drop the six *_cli.py companions unless a domain truly needs a separate entry surface

### FINDING_9:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/implement-finalize.sh:486-526
- **Concern**: Partial cutover for implement-finalize is implied but not listed in Files to modify/create. Scenario: `check-remote-branch.sh` is the only non-deferred script in implement-finalize's postbump gate; deleting it before repointing this sole live caller breaks `LARCH_SHIP_PR_IMPL=bash` Step 8b while deferred `rebase-push.sh` / `git-force-push.sh` must stay bash until E1
- **Proposed resolution**: Add `scripts/implement-finalize.sh` to UPDATED with an explicit partial cutover: repoint only `check-remote-branch.sh` to `python3 "$PLUGIN_ROOT/python/cli.py" git check-remote-branch`; keep deferred bash invocations unchanged until E1

### FINDING_10:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:113-114
- **Concern**: 1. [SCOPE-REDUCTION] Plan allows porting `scripts/append-execution-issue.sh` inside the phantom Python surface even though B1 only absorbs the listed git/gh/CI helpers. Scenario: Implementer may duplicate or alter the execution-issue append contract while migrating phantom probes, expanding the PR beyond B1 and risking changed warning formatting or failure folding for existing callers
- **Proposed resolution**: Remove the "or ports it byte-identically" option; require `probe_with_warn` to subprocess the existing `scripts/append-execution-issue.sh` and leave that script untouched.

### FINDING_11:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:56-57,161-167;scripts/implement-finalize.sh:486
- **Concern**: check-remote-branch.sh deletion path omits implement-finalize.sh cutover or E1 deferral. Scenario: Plan allows deleting scripts/check-remote-branch.sh after finalize.py gains git.remote_branch_state, but the only live bash caller is implement-finalize.sh postbump (invoked from ship-pr.sh on LARCH_SHIP_PR_IMPL=bash). check-remote-branch is absent from Deferred-to-E1 and implement-finalize.sh is not listed under Files to modify
- **Proposed resolution**: Add check-remote-branch to Deferred-to-E1 (simplest minimum-change) OR add ### UPDATED: scripts/implement-finalize.sh repointing the postbump gate to python3 "$PLUGIN_ROOT/python/cli.py" git check-remote-branch before bash deletion; update scripts/test-implement-finalize.sh stubs accordingly

### FINDING_12:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:178; scripts/ci-decide.sh:41-75; scripts/merge-pr.sh:20-22,83-95; scripts/ci-rerun-failed.sh:20-47; scripts/phantom-probe-with-warn.sh:12-29
- **Concern**: The plan’s “always-exit-0-with-status” list overstates several CLI contracts. Scenario: Following the plan as written can make `merge pr`, `ci rerun-failed`, `ci decide`, or `git phantom-probe` return success on invalid argv, drifting from the retired scripts’ usage-error exits required by exact parity
- **Proposed resolution**: Revise the edge-case table to say these commands exit 0 only after valid-argv status paths; preserve usage exits from the scripts (`merge-pr`/`ci-rerun-failed`/`ci-decide` exit 1, `phantom-probe-with-warn` exits 2) and pin those CLI invalid-argv cases in the new contract tests.

### FINDING_13:
- **Reviewer(s)**: Cursor-dyn-parity-map
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/git.py:575-644
- **Concern**: The push-domain row cites `force_push_recovery` in `push.py`, but the function already lives in `git.py`.. Scenario: An implementer adds a second force-push implementation in `push.py` instead of wiring `git.force_push_recovery` through `push_cli`, duplicating logic and drifting STATUS/exit mapping.
- **Proposed resolution**: Retarget the mapping row and `### UPDATED: python/push.py` note to `git.force_push_recovery`; keep `push_cli` as the thin KV/exit wrapper only.

### FINDING_14:
- **Reviewer(s)**: Cursor-dyn-parity-map
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/git.py:86-103
- **Concern**: The `lib-count-commits` row backs on `rev_count`/`rev_list_count`, but `rev_count` raises via `_ensure_success` on `git rev-list` failure.. Scenario: `scripts/lib-count-commits.sh` always prints an integer and exits 0, writing `git_error` to `COUNT_COMMITS_STATUS_FILE`; wrapping `rev_count` would break `verify-skill-called.sh` semantics.
- **Proposed resolution**: Keep the row **partial** but name the planned `count_commits` helper (main/origin/main fallback, forced 0, status side-channel) as the sole backing—not `rev_count`.

### FINDING_15:
- **Reviewer(s)**: Cursor-dyn-parity-map
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/rebase.py:81-82
- **Concern**: The `git-rebase-abort` row is **gap**, yet `_abort_rebase` already exists and propagates `git rebase --abort` failures.. Scenario: `scripts/git-rebase-abort.sh` always exits 0 (`|| true`); reusing `_abort_rebase` for the CLI would regress conflict-resolution callers expecting idempotency.
- **Proposed resolution**: Call out in the gap row that `_abort_rebase` is ship-only; add a new idempotent `rebase_abort` that swallows all failures before `git_cli` wraps it.

### FINDING_16:
- **Reviewer(s)**: Cursor-dyn-parity-map
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/git.py:558-643
- **Concern**: The `git-force-push` **partial** row lists bash STATUS literals only; `ForcePushResult.status` also emits `detached_head`, `branch_mismatch`, and `status_failed`.. Scenario: Bash maps detached HEAD and porcelain-probe failure to exit **2** with a narrower STATUS set; a CLI that emits only the four documented literals mis-classifies guard failures.
- **Proposed resolution**: Extend the partial row (or `push_cli` contract) with the full Python→bash STATUS/exit map for every `ForcePushResult.status`.

### FINDING_17:
- **Reviewer(s)**: Cursor-dyn-parity-map
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/rebase.py:45-69
- **Concern**: The `git-sync-local-main` **gap** row omits that `_sync_local_main` already exists with a ship contract.. Scenario: It raises `Stalled` on `main` and emits no `RESULT=updated|absent|already_current`; porting the bash script by calling `_sync_local_main` would break KV/exit parity.
- **Proposed resolution**: Note in the gap row that `_sync_local_main` is not the backing; implement new `sync_local_main` returning `RESULT` and exit 0/1 per `scripts/git-sync-local-main.sh`.

### FINDING_18:
- **Reviewer(s)**: Codex-dyn-parity-map
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:71; python/gh.py:150-164,688-709; scripts/gh-pr-body-update.sh:54-62,94-113; scripts/test-gh-pr-body-update.sh:43-70
- **Concern**: `gh-pr-body-update` is marked have, but `gh.pr_edit_body` is not parity. Scenario: Current Python requires `--repo`, always writes a redacted temp body, and lacks the transient retry pinned by the bash harness; a direct CLI wrapper would change PR body bytes, fail no-repo calls, or lose retry behavior
- **Proposed resolution**: Relabel this row partial and add/update a typed body-update parity function that accepts optional repo, preserves body-file contents, performs transient retry, and emits the existing UPDATED/ERROR exit contract

### FINDING_19:
- **Reviewer(s)**: Codex-dyn-parity-map
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:92; python/ci_monitor.py:273-288,349-356; scripts/ci-status.sh:27-35,76-83,198-203
- **Concern**: `ci-status` partial understates missing fail-open behavior. Scenario: The plan only calls out text fallback, but current `gather_status` returns `status=error` on `gh pr view` failure and can raise during squash-merge race probing, while the shell keeps default output and continues/fails open on those probes
- **Proposed resolution**: Add the ci-status parity work to preserve the shell trap/default contract: always emit the four KVs, reserve `CI_STATUS=error` for argument errors, and treat PR-view/git-log probe failures like the bash path

### FINDING_20:
- **Reviewer(s)**: Codex-dyn-parity-map
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:58-63,125-126; python/push.py:41-73; python/git.py:575-584
- **Concern**: `git-force-push` is assigned to `push.py`, but the existing backing function is in `git.py`. Scenario: Following the plan literally either duplicates `force_push_recovery` in `push.py` or makes `push_cli` target a function that does not exist there, despite existing `pr.py` callers using `git.force_push_recovery`
- **Proposed resolution**: Revise the mapping and files section so `push force` reuses/extends `python/git.py::force_push_recovery`, or explicitly plan a move plus all import updates

### FINDING_21:
- **Reviewer(s)**: Codex-dyn-parity-map
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:98-114
- **Concern**: [SCOPE-REDUCTION] The plan creates `python/phantom.py` outside the scoped existing consolidation surfaces. Scenario: The issue scope asks consolidation into existing Python surfaces plus CLI verbs; adding a new runtime module expands architecture for two phantom/check scripts instead of using the existing `git`/checks surface the plan already exposes via `git phantom-probe`
- **Proposed resolution**: Do not add `python/phantom.py`; home the phantom parity functions in an existing in-scope module, preferably the module backing the `git` CLI verbs, unless the plan explicitly re-scopes this with justification

### FINDING_22:
- **Reviewer(s)**: Cursor-dyn-deletion-gate
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:161-167; scripts/implement-finalize.sh:486
- **Concern**: Deferred-to-E1 omits check-remote-branch despite ship-pr closure via implement-finalize. Scenario: Recursive walk from ship-pr.sh reaches implement-finalize.sh postbump which live-invokes "$SCRIPT_DIR/check-remote-branch.sh" (line 486). The explicit retention list (line 165) omits it; line 167 says defer unless implement-finalize is repointed, but Files to modify has no scripts/implement-finalize.sh entry—only python/finalize.py (lines 143-144). An implementer can delete check-remote-branch.sh after Python finalize repoint alone, breaking LARCH_SHIP_PR_IMPL=bash Step 8b force-push gate.
- **Proposed resolution**: [SCOPE-REDUCTION] Add check-remote-branch to the line-165 Deferred-to-E1 list (simplest B1 path). If deletion in B1 is intended, add UPDATED scripts/implement-finalize.sh repointing line 486 to the git check-remote-branch CLI before any bash deletion.

### FINDING_23:
- **Reviewer(s)**: Cursor-dyn-deletion-gate
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:13-19; plan.txt:183; python/migration_lint.py:155-159; docs/python-migration.md:63-66
- **Concern**: migration_lint upgrade spec conflates F17 path precision with F18 ship-pr live-only filtering. Scenario: Line 183 tags both F17 and F18 as live-only migration_lint behavior, but F17 is no bare-basename / manifest+$SCRIPT_DIR-derived matching repo-wide (lines 14, 190-191) while F18 is ship-pr.sh live-invocation-only deletion blocking (lines 15-16). Current migration_lint.py only does full-path substring checks (lines 156-157); docs/python-migration.md still documents full-path-only (lines 63-66). Misread risks shipping substring upgrade without repo-wide $SCRIPT_DIR-derived matching, missing live bash callers like "$SCRIPT_DIR/resolve-repo.sh" after cutover slips.
- **Proposed resolution**: Split the contract in plan + docs/python-migration.md: repo-wide manifest path + $SCRIPT_DIR/<basename>.sh derived patterns for lint-retired-scripts; F18 live-invocation filter only for classifying ship-pr.sh retention/deletion blockers (separate from comment mentions at scripts/ship-pr.sh:976).

### FINDING_24:
- **Reviewer(s)**: Codex-dyn-deletion-gate
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:161-167; scripts/implement-finalize.sh:398-400; scripts/timing-report.sh:42-54
- **Concern**: [SCOPE-REDUCTION] Deferred-to-E1 says it is the recursive ship-pr closure, but omits read-workflow-path even though implement-finalize calls timing-report and timing-report invokes $SCRIPT_DIR/read-workflow-path.sh. Scenario: If B1 deletes scripts/read-workflow-path.sh without repointing this ship-pr-closure edge, the legacy bash ship-pr path loses its workflow fallback; if migration_lint catches it, the plan stalls at deletion instead
- **Proposed resolution**: Add read-workflow-path to Deferred-to-E1, or explicitly require scripts/timing-report.sh to be cut over before scripts/read-workflow-path.sh is eligible for deletion

### OOS_1:
- **Description**: [SCOPE-REDUCTION] Six new *_cli.py companions vs in-module CLI entrypoints. Scenario: ship.py registers main inside the domain module; report_tokens_cli.py is the exception for a large pipeline. Six thin wrappers add files and registry indirection without changing runtime behavior
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: <TMPDIR>/plan.txt:110-117
- **Phase**: design

### OOS_2:
- **Description**: `rebase_and_push` is ship-oriented (conflict launch, `Stalled`/`TransientNetworkError`) and is not the `rebase-push.sh` primitive the checkpoint row needs.. Scenario: Not a B1 correctness bug if the plan keeps `push rebase`/`push checkpoint-probe` as **gap**; relevant only if someone tries to satisfy those verbs by thin-wrapping `rebase_and_push`.
- **Reviewer**: Cursor-dyn-parity-map
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/rebase.py:312-397
- **Phase**: design
