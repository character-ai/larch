### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:59-60
- **Concern**: Edge cases claim a no-retry assertion for pending/failing `gh pr checks`, but the Testing strategy section does not add that case. Scenario: Regression of failure mode 1 (over-retry on real pending/failing checks) could ship with no harness signal; mitigation text is currently aspirational
- **Proposed resolution**: Add an explicit `test-merge-pr.sh` sub-test: stub `gh pr checks` exits non-zero once with pending/failing output that does not match `is_transient_net_signature`, assert a single invocation (or call-count == 1) and conservative `CI_GOOD=false` / `ci_not_ready`

### FINDING_2:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: nit
- **Focus area**: correctness
- **Location**: plan.txt:58-59
- **Concern**: Edge cases claim a no-retry test that the Testing strategy never adds. Scenario: Edge cases says pending/failing `gh pr checks` non-zero exits are "covered by a no-retry assertion in the test", but lines 41-42 only plan transient-then-success cases; `scripts/test-merge-pr.sh` stub `checks` always exits 0, so a mis-wrap that retries on non-zero pending would not be caught
- **Proposed resolution**: Either add one planned stub case (`exit 1` + pending JSON, assert `pr checks` count stays 1) or delete the "covered by a no-retry assertion" clause and rely on the predicate rationale only

### FINDING_3:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: agent-lint.toml:1013-1034
- **Concern**: Plan adds a new Makefile-only rebase-push harness but omits agent-lint exclusions. Scenario: Existing adjacent rebase-push harnesses are excluded because agent-lint does not follow Makefile-only reachability; the new scripts/test-rebase-push-no-push-fetch-retry.sh and .md sibling can make make lint or relevant-checks fail even though the Makefile target is wired
- **Proposed resolution**: Add the new .sh exclusion beside the other test-rebase-push harness entries and add the .md exclusion beside scripts/test-rebase-push-*.md

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation, Codex-Innovation, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: agent-lint.toml:1013-1034
- **Concern**: New Makefile-only rebase-push harness is not added to agent-lint excludes. Scenario: The plan creates scripts/test-rebase-push-no-push-fetch-retry.sh and .md, but existing sibling rebase-push harnesses are explicitly excluded because agent-lint dead-script reachability does not follow Makefile-only references; relevant-checks runs agent-lint, so the planned validation can fail after the PR lands
- **Proposed resolution**: Add scripts/test-rebase-push-no-push-fetch-retry.sh and scripts/test-rebase-push-no-push-fetch-retry.md to agent-lint.toml beside the existing test-rebase-push-* exclusions, or add a real non-Makefile runtime reference if that is intended

### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/create-pr.sh:192-220
- **Concern**: Recovery `with_transient_retry` must be `set -e`-safe inside `recover_existing_pr_after_create_conflict`. Scenario: A bare `with_transient_retry ...` (or `pr_json=$(with_transient_retry ...)`) exits the script before lines 212-215; persistent `gh pr list` failure never reaches the conflict-text URL fallback the plan keeps as tier 2
- **Proposed resolution**: Wrap in `if with_transient_retry ...; then pr_json=$_WTR_OUT; else pr_json=$_WTR_OUT; fi` (or `|| true` before assigning), matching the existing `create_fail_file` block at lines 265-277

### FINDING_6:
- **Reviewer(s)**: Codex-dyn-shell-compat
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: agent-lint.toml:1013-1035, agent-lint.toml:1392-1395
- **Concern**: The plan adds scripts/test-rebase-push-no-push-fetch-retry.sh and its .md sibling but does not add them to agent-lint's Makefile-only harness exclusions.. Scenario: After the proposed Makefile wiring, bash scripts/relevant-checks.sh still runs agent-lint; existing sibling rebase-push harnesses are explicitly excluded because agent-lint does not follow Makefile-only references, so the new harness can fail structural checks even if the Bash 3.2 constructs are valid.
- **Proposed resolution**: Add scripts/test-rebase-push-no-push-fetch-retry.sh next to the existing rebase-push harness exclusions and scripts/test-rebase-push-no-push-fetch-retry.md next to the existing rebase-push .md exclusions, with the same short Makefile-only rationale.

### FINDING_7:
- **Reviewer(s)**: Cursor-dyn-harness-fidelity
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-merge-pr.sh:48-87
- **Concern**: Plan says transient view/checks tests reuse GH_VIEW_COUNT_FILE / GH_CHECKS_COUNT_FILE flip pattern, but those branches only change success JSON on call ≥2 and never exit 1 with a net signature on call 1. Scenario: Implementer sets only GH_VIEW_SECOND_* / GH_CHECKS_SECOND_JSON; stub still returns HTTP-200-style JSON on every call, so with_transient_retry is never exercised and new cases can pass while production merge-pr wraps stay untested
- **Proposed resolution**: Add env-gated stub branches (e.g. fail call 1 with stderr matching is_transient_net_signature, succeed on call 2) in write_fake_gh view and checks handlers; document required env vars beside the two new run_case blocks

### FINDING_8:
- **Reviewer(s)**: Codex-dyn-harness-fidelity
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-merge-pr.sh:47-88
- **Concern**: The plan says to reuse the existing GH_VIEW_COUNT_FILE/GH_CHECKS_COUNT_FILE flip pattern for first-call transient failures, but the current view/checks dispatch only flips returned JSON and never exits non-zero or emits a network signature.. Scenario: A test added with only GH_VIEW_SECOND_* or GH_CHECKS_SECOND_JSON exercises normal content flipping, not with_transient_retry; the planned retry coverage can pass or fail for the wrong reason.
- **Proposed resolution**: Add explicit first-call transient branches inside the view and checks cases, keyed by new env vars and the existing count files, that print a net-signature diagnostic to stderr and exit 1 on count 1, then return valid JSON on the next call.

### FINDING_9:
- **Reviewer(s)**: Cursor-dyn-net-sig-coverage, Codex-dyn-net-sig-coverage
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lib-net.sh:10-14; scripts/create-pr.sh:201-207; scripts/merge-pr.sh:113-156; scripts/rebase-push.sh:195-198
- **Concern**: The plan relies on the current transient signature set, but that set does not cover common gh DNS text such as "lookup api.github.com: no such host" and does not cover capitalized "Connection reset by peer" unless another substring also appears.. Scenario: gh pr list/view/checks DNS failures from Go's resolver can exhaust after one attempt because they do not contain "Could not resolve"; SSH git fetch connection resets can similarly miss the lowercase-only "connection reset" pattern.
- **Proposed resolution**: Add the minimum new lib-net signatures plus test fixtures: e.g. lookup + no such host, no such host, and capitalized Connection reset. Keep the three call-site wrappers unchanged.

### FINDING_10:
- **Reviewer(s)**: Cursor-dyn-net-sig-coverage, Codex-dyn-net-sig-coverage
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lib-net.sh:36-54; scripts/merge-pr.sh:133-163
- **Concern**: The plan's CHECKS_JSON empty-on-exhaustion contract conflicts with the proposed "set CHECKS_JSON/CHECKS_TEXT from _WTR_OUT" wording. with_transient_retry leaves _WTR_OUT as the final attempt's stdout on exhaustion; it does not clear it.. Scenario: If an exhausted gh pr checks attempt emits transient text on stdout, CHECKS_JSON is non-empty invalid JSON and the fallback text path can consume non-empty error text; text that lacks fail/pending words could mark CI_GOOD=true.
- **Proposed resolution**: Specify the merge-pr capture logic precisely: on wrapper failure whose final fail file still matches is_transient_net_signature, set CHECKS_JSON and CHECKS_TEXT to empty; preserve _WTR_OUT only for non-transient gh pr checks exits so pending/failing check output remains available.
