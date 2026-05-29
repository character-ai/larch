### FINDING_1: Missing no-retry coverage for pending/failing checks
- **Reviewer(s)**: Cursor-Arch, Cursor-Edge
- **Severity**: important
- **Concern**: The plan claims pending/failing `gh pr checks` non-zero exits are covered by a no-retry assertion, but the testing strategy only covers transient-then-success behavior, so a regression that retries real CI failures could ship undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add an explicit `test-merge-pr.sh` sub-test: stub `gh pr checks` exits non-zero once with pending/failing output that does not match `is_transient_net_signature`, assert a single invocation (or call-count == 1) and conservative `CI_GOOD=false` / `ci_not_ready`
  - From Cursor-Edge: Either add one planned stub case (`exit 1` + pending JSON, assert `pr checks` count stays 1) or delete the "covered by a no-retry assertion" clause and rely on the predicate rationale only


### FINDING_2: Missing agent-lint exclusions for new Makefile-only rebase-push harness
- **Reviewer(s)**: Codex-Edge, Cursor-Innovation, Codex-Innovation, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements, Codex-dyn-shell-compat
- **Severity**: important
- **Concern**: The new `scripts/test-rebase-push-no-push-fetch-retry.sh` harness and `.md` sibling are Makefile-only references, matching existing harnesses that need `agent-lint.toml` exclusions; without those exclusions, `relevant-checks` or `make lint` may fail even though the Makefile wiring exists.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Add the new .sh exclusion beside the other test-rebase-push harness entries and add the .md exclusion beside scripts/test-rebase-push-*.md
  - From Cursor-Innovation, Codex-Innovation, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements: Add scripts/test-rebase-push-no-push-fetch-retry.sh and scripts/test-rebase-push-no-push-fetch-retry.md to agent-lint.toml beside the existing test-rebase-push-* exclusions, or add a real non-Makefile runtime reference if that is intended
  - From Codex-dyn-shell-compat: Add scripts/test-rebase-push-no-push-fetch-retry.sh next to the existing rebase-push harness exclusions and scripts/test-rebase-push-no-push-fetch-retry.md next to the existing rebase-push .md exclusions, with the same short Makefile-only rationale.


### FINDING_3: Recovery retry wrapper must preserve fallback under `set -e`
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: Wrapping `gh pr list` in `recover_existing_pr_after_create_conflict` must not let a persistent retry failure terminate the script before the existing conflict-text URL fallback runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Wrap in `if with_transient_retry ...; then pr_json=$_WTR_OUT; else pr_json=$_WTR_OUT; fi` (or `|| true` before assigning), matching the existing `create_fail_file` block at lines 265-277


### FINDING_4: Planned merge-pr retry harness does not actually simulate transient failures
- **Reviewer(s)**: Cursor-dyn-harness-fidelity, Codex-dyn-harness-fidelity
- **Severity**: important
- **Concern**: The proposed `GH_VIEW_COUNT_FILE` / `GH_CHECKS_COUNT_FILE` reuse only flips successful JSON content today; it does not make the first call exit non-zero with a transient network signature, so tests could pass without exercising `with_transient_retry`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-harness-fidelity: Add env-gated stub branches (e.g. fail call 1 with stderr matching is_transient_net_signature, succeed on call 2) in write_fake_gh view and checks handlers; document required env vars beside the two new run_case blocks
  - From Codex-dyn-harness-fidelity: Add explicit first-call transient branches inside the view and checks cases, keyed by new env vars and the existing count files, that print a net-signature diagnostic to stderr and exit 1 on count 1, then return valid JSON on the next call.


### FINDING_5: Transient signature set misses common DNS and reset errors
- **Reviewer(s)**: Cursor-dyn-net-sig-coverage, Codex-dyn-net-sig-coverage
- **Severity**: important
- **Concern**: The current network signature predicate may not classify common `gh` DNS failures like `lookup api.github.com: no such host`, or capitalized `Connection reset by peer`, causing intended retry wrappers to give up after one attempt.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-net-sig-coverage, Codex-dyn-net-sig-coverage: Add the minimum new lib-net signatures plus test fixtures: e.g. lookup + no such host, no such host, and capitalized Connection reset. Keep the three call-site wrappers unchanged.


### FINDING_6: Exhausted transient checks can leave invalid stdout in CHECKS_JSON
- **Reviewer(s)**: Cursor-dyn-net-sig-coverage, Codex-dyn-net-sig-coverage
- **Severity**: important
- **Concern**: The plan’s empty-on-exhaustion contract conflicts with assigning `CHECKS_JSON` / `CHECKS_TEXT` from `_WTR_OUT`, because `with_transient_retry` preserves the final stdout; exhausted transient output could become non-empty invalid JSON or misleading fallback text.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-net-sig-coverage, Codex-dyn-net-sig-coverage: Specify the merge-pr capture logic precisely: on wrapper failure whose final fail file still matches is_transient_net_signature, set CHECKS_JSON and CHECKS_TEXT to empty; preserve _WTR_OUT only for non-transient gh pr checks exits so pending/failing check output remains available.

