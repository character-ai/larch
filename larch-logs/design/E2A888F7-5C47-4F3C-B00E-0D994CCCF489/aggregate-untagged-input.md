### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: minor
- **Focus area**: correctness
- **Location**: plan.txt:35-39,108
- **Concern**: The templated issue-view wrapper has conflicting failure contracts. Its implementation says to return the `_retry_read` `CommandResult`, while the failure modes say non-transient failures raise `ShipError` and transient failures raise `TransientNetworkError`.. Scenario: An implementer may choose either behavior, producing incompatible callers and tests. The new wrapper's error handling also diverges from the stated policy that new typed reads use `_raise_read_failure`.
- **Proposed resolution**: Choose one contract and state it consistently. If the wrapper returns `CommandResult`, remove the raising failure-mode requirement and test failed results. If it is a typed read, call `_raise_read_failure` after retries and test both ordinary and exhausted transient failures.

### FINDING_2:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/git/gh.py:planned issue_view_template_read
- **Concern**: Templated issue-view failure handling conflicts with the plan's stated read-error contract. Scenario: The wrapper is specified to return `_retry_read`'s `CommandResult`, but the failure modes require non-transient failures to raise `ShipError` and exhausted transient failures to raise `TransientNetworkError`. A sibling caller that adopts the wrapper can therefore receive a failed result instead of the promised exception, bypassing the shared read-error authority.
- **Proposed resolution**: Check the returned result with `_raise_read_failure` before returning, or revise the failure-mode contract to explicitly preserve failed `CommandResult` values.

### FINDING_3:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: minor
- **Focus area**: code-quality
- **Location**: python/larch/git/gh.py:1498-1525 and planned issue-view additions
- **Concern**: The view audit still leaves plain `gh issue view <issue>` shapes without a public wrapper. Scenario: The audited callers include no-`--json` view commands in `design_step0.py` and `issue_create.py`. The planned template wrapper covers only `--json ... --template`, while the existing helpers all require `--json`. Those callers cannot later repoint to a wrapper without retaining raw issue-view construction, so the stated view-wrapper coverage remains incomplete.
- **Proposed resolution**: Add a retrying plain-view wrapper for `gh issue view <issue>` with optional `repo` and `cwd`, or explicitly document and justify excluding these audited shapes from the coverage goal.

### FINDING_4:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/git/gh.py:planned issue_close
- **Concern**: The planned close wrapper does not define argument placement for all audited close forms. Scenario: Existing callers use both `gh issue close <issue> --repo <repo> ...` and `gh issue close --repo <repo> <issue> ...`. The proposed wrapper fixes one ordering, so sibling repointing must rely on `gh` accepting reordered options rather than preserving the audited command grammar. If the wrapper is intended as the single close authority, its accepted semantic forms and ordering guarantee need to be explicit.
- **Proposed resolution**: State that the wrapper intentionally canonicalizes all close calls to `issue` followed by optional flags, and verify that ordering with the supported `gh issue close` grammar; otherwise provide an API that preserves the required repository-before-issue form.

### FINDING_5:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/issue/issue_create.py:928
- **Concern**: The planned wrappers leave the audited plain `gh issue view <issue>` shape uncovered. Scenario: `issue_create.py` invokes issue view without `--json`; existing field helpers and the planned template helper cannot represent this command, so the explicit view-shape coverage goal remains incomplete
- **Proposed resolution**: Add a minimal read wrapper for plain issue view, returning `CommandResult` through `_retry_read`, plus exact argv coverage

### FINDING_6:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: plan.txt:7-9,35-39,106-111
- **Concern**: The templated-view failure contract is contradictory. Scenario: The wrapper bullet says `_retry_read` returns `CommandResult`, while the approach and failure modes require `_raise_read_failure` and exceptions; implementation may raise instead of preserving an inspectable failed result, or silently violate the stated failure contract
- **Proposed resolution**: Choose one contract explicitly; preserve the existing `*_read` seam by returning the final failed `CommandResult` after retries, remove the templated-view exception claim, and test a non-transient failed result

### FINDING_7:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: plan.txt:7-9,35-39,108-109
- **Concern**: Templated issue-view failure contract is contradictory. Scenario: The wrapper-specific step says `issue_view_template_read` returns `CommandResult`, while the general read policy and failure modes require `_raise_read_failure` and exceptions. An implementation cannot satisfy both contracts, and sibling caller repointing may either lose inspectable failures or receive unexpected exceptions. The prior-round return-contract fix is incomplete.
- **Proposed resolution**: Choose one contract consistently. Prefer the established `*_read` contract: return the final `CommandResult`, including non-zero results after retries. Remove `_raise_read_failure` and exception claims for this wrapper, and test ordinary and exhausted transient failures as returned results.
