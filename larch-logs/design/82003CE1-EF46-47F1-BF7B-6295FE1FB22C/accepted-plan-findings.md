### FINDING_1: Unsafe `with_transient_retry` call shape under `set -e`
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Codex-Innovation, Codex-Requirements
- **Severity**: important
- **Concern**: Bare `with_transient_retry` calls in scripts running with `set -e` can exit before callers read `_WTR_RC` / `_WTR_OUT`, bypassing existing structured failure handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch, Codex-Arch: Require every errexit caller to invoke the helper in an if/set+e guarded shape before reading _WTR_RC, or make the shared wrapper contract return 0 and communicate status only through _WTR_RC
  - From Codex-Innovation: Require each set -e callsite to invoke the helper in an if/set +e guard, then copy _WTR_RC and _WTR_OUT before restoring existing error handling
  - From Codex-Requirements: Revise the plan to require each set -e callsite to invoke the helper in a conditional or set +e capture block, then read _WTR_OUT and _WTR_RC before restoring the existing error handling


### FINDING_2: `ship_pr_with_transient_retry` treats exhausted rc=0 envelopes as success
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Codex-Edge, Cursor-Innovation, Codex-Innovation, Cursor-dyn-wrapper-rename-regression, Codex-dyn-wrapper-rename-regression, Cursor-Pragmatic, Codex-Pragmatic, Codex-Requirements
- **Severity**: important
- **Concern**: `merge-pr.sh` and `ci-wait.sh` can emit transient failure envelopes while exiting 0; after retry exhaustion, the proposed wrapper can return success instead of preserving `exit_transient_net` / exit 6 behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch, Codex-Arch: Change the wrapper to re-run the passed predicate against the final fail_file content before any rc==0 return, and call exit_transient_net when the predicate still marks the envelope transient
  - From Codex-Edge: After with_transient_retry, re-run the final predicate against the fail_file before any rc==0 return, or have lib-net expose an exhausted-transient flag; call exit_transient_net when the final envelope is still transient
  - From Cursor-Innovation: After with_transient_retry, read fail_file content and call exit_transient_net when "$pred" "$ff_content" is true (keep the existing rc!=0 plus is_transient_net_signature branch for predicate_none callsites)
  - From Codex-Innovation, Cursor-dyn-wrapper-rename-regression, Codex-dyn-wrapper-rename-regression: Have with_transient_retry expose an exhausted-transient flag, or otherwise let ship_pr_with_transient_retry detect predicate exhaustion before any rc=0 return
  - From Cursor-Pragmatic, Codex-Pragmatic: When attempt 3 is still transient, return a non-zero code or expose an exhausted-transient flag; add a test asserting rc=0 predicate exhaustion is not reported as success
  - From Codex-Requirements: Add a final predicate check in ship_pr_with_transient_retry against "$2" even when _WTR_RC is 0, and add a test that exhausted MERGE_RESULT=error or ACTION=bail envelopes still trigger ship-pr transient exit semantics


### FINDING_3: `check-remote-branch.sh` loses stderr diagnostics after retry wrapping
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Concern**: Keeping `STDERR_TMP` while `with_transient_retry` writes stderr to `fail_file` can leave `ERROR=` rows empty or generic, losing transport/auth diagnostics and redaction input.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: In the check-remote-branch section, require building STDERR_FLAT from fail_file (or _WTR_OUT plus fail_file) after with_transient_retry; drop or repurpose STDERR_TMP so ERROR= stays populated


### FINDING_4: Generic retry is unsafe for non-idempotent issue creation
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Concern**: Retrying `gh issue create` can duplicate issues if the server-side create succeeds but the response is lost, and existing orphan handling cannot close an issue number it never received.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Keep issue-create calls bare for this SIMPLE lane, or add callsite-specific recovery before retry using a stable existing-issue lookup or idempotency marker


### FINDING_5: Design-log remote branch cleanup can delete a branch for an existing PR
- **Reviewer(s)**: Codex-Edge, Cursor-Pragmatic, Codex-Pragmatic
- **Severity**: important
- **Concern**: PR creation may succeed server-side while URL parsing or recovery listing fails; unconditional cleanup in that uncertain state can delete the remote branch backing an open PR.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Only delete after a successful recovery probe positively confirms no PR; on list failure or uncertainty, preserve the branch and emit RECOVERY_BRANCH
  - From Cursor-Pragmatic, Codex-Pragmatic: Guard the cleanup with create_rc != 0, or split the failed-create path from the parse/list-recovery path before deleting the remote branch


### FINDING_6: Retrying `git clone` against a fixed directory is not idempotent
- **Reviewer(s)**: Codex-Edge, Codex-Innovation
- **Severity**: latent
- **Concern**: A failed clone can leave the target directory behind, causing the next retry to fail with a local “destination exists” error rather than retrying the network operation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Use a tiny callsite wrapper that removes the partial clone_dir before retry, or retry into per-attempt clone directories and use the successful one
  - From Codex-Innovation: Drop the git clone wrap from this minimum-change plan, or add explicit cleanup of clone_dir between retry attempts if clone retry is truly required


### FINDING_7: Existing-PR title sync `gh pr edit` remains unwrapped
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements, Cursor-dyn-callsite-gap-audit, Codex-dyn-callsite-gap-audit
- **Severity**: important
- **Concern**: The `scripts/ship-pr.sh` existing-PR title update around `:1622` is omitted from the plan, leaving a Tier 1 audited `gh pr edit` call exposed to transient GitHub API failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Extend the `scripts/ship-pr.sh` section: wrap :1622 with `ship_pr_with_transient_retry` (reuse the existing `fail_file` / `record_failure` path) and :2761 with the same wrapper or document an explicit audit exception if best-effort `|| true` is intentional
  - From Codex-Requirements: Add these two gh pr edit invocations to the plan's ship-pr.sh section and wrap them with ship_pr_with_transient_retry or with_transient_retry while preserving their existing hard-fail vs best-effort behavior
  - From Cursor-dyn-callsite-gap-audit: Add an explicit plan bullet: wrap `gh pr edit ... --title` at :1622 with `ship_pr_with_transient_retry transient_envelope_predicate_none "$fail_file" ...`, read `_WTR_RC`/`_WTR_OUT`, and keep the existing `record_failure` branch
  - From Codex-dyn-callsite-gap-audit: Add explicit bullets in the scripts/ship-pr.sh section to wrap both gh pr edit callsites, preserving record_failure behavior at :1622 and best-effort title-update behavior at :2761


### FINDING_8: Post-rebump best-effort `gh pr edit` remains unwrapped
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements, Cursor-dyn-callsite-gap-audit, Codex-dyn-callsite-gap-audit
- **Severity**: important
- **Concern**: The `scripts/ship-pr.sh` post-rebump title update around `:2761` is omitted from the plan, leaving a best-effort `gh pr edit` call single-shot on transient failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Extend the `scripts/ship-pr.sh` section: wrap :1622 with `ship_pr_with_transient_retry` (reuse the existing `fail_file` / `record_failure` path) and :2761 with the same wrapper or document an explicit audit exception if best-effort `|| true` is intentional
  - From Codex-Requirements: Add these two gh pr edit invocations to the plan's ship-pr.sh section and wrap them with ship_pr_with_transient_retry or with_transient_retry while preserving their existing hard-fail vs best-effort behavior
  - From Cursor-dyn-callsite-gap-audit: Add a plan bullet for :2761: wrap with `with_transient_retry transient_envelope_predicate_none` (not `ship_pr_with_transient_retry`, to preserve best-effort semantics) and retain `|| true` after reading `_WTR_RC`
  - From Codex-dyn-callsite-gap-audit: Add explicit bullets in the scripts/ship-pr.sh section to wrap both gh pr edit callsites, preserving record_failure behavior at :1622 and best-effort title-update behavior at :2761


### FINDING_9: Merge retry globals can be overwritten before failure reporting
- **Reviewer(s)**: Cursor-dyn-global-state-contract, Codex-dyn-global-state-contract
- **Severity**: important
- **Concern**: Successive merge wrappers can overwrite `_WTR_OUT` / `_WTR_RC`; without immediate capture after the admin merge, the fallback merge can erase or duplicate the admin failure detail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-global-state-contract, Codex-dyn-global-state-contract: Amend the merge-pr section to say each wrapped merge call must immediately copy _WTR_OUT/_WTR_RC into ADMIN_OUTPUT/ADMIN_EXIT or MERGE_OUTPUT/MERGE_EXIT before any later with_transient_retry call


### FINDING_10: Design-log retry wrappers need per-call files and immediate captures
- **Reviewer(s)**: Cursor-dyn-global-state-contract, Codex-dyn-global-state-contract
- **Severity**: important
- **Concern**: Reusing a single `fail_file` or delaying capture across push, create, and merge wrappers can let later calls truncate or overwrite the result a failure branch needs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-global-state-contract, Codex-dyn-global-state-contract: Spell out push_fail_file/create_fail_file/merge_fail_file via mktemp and immediate push_rc/create_rc/merge_rc plus output captures after each with_transient_retry call

