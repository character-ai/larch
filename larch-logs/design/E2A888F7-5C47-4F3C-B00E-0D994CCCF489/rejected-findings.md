### [Plan Review] FINDING_1

### FINDING_1: Templated issue-view failure contract is contradictory
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Codex-Pragmatic, Codex-Requirements
- **Severity**: major
- **Concern**: The planned templated issue-view wrapper has conflicting contracts: one description returns `_retry_read`'s `CommandResult`, while the general read policy and failure modes require `_raise_read_failure` and typed exceptions. This leaves callers and tests ambiguous about whether failed reads remain inspectable results or raise, and may bypass the shared read-error authority.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Choose one contract and state it consistently. If the wrapper returns `CommandResult`, remove the raising failure-mode requirement and test failed results. If it is a typed read, call `_raise_read_failure` after retries and test both ordinary and exhausted transient failures.
  - From Codex-Innovation: Check the returned result with `_raise_read_failure` before returning, or revise the failure-mode contract to explicitly preserve failed `CommandResult` values.
  - From Codex-Pragmatic: Choose one contract explicitly; preserve the existing `*_read` seam by returning the final failed `CommandResult` after retries, remove the templated-view exception claim, and test a non-transient failed result
  - From Codex-Requirements: Choose one contract consistently. Prefer the established `*_read` contract: return the final `CommandResult`, including non-zero results after retries. Remove `_raise_read_failure` and exception claims for this wrapper, and test ordinary and exhausted transient failures as returned results.


### [Plan Review] FINDING_3

### FINDING_3: Issue-close wrapper argument ordering is underspecified
- **Reviewer(s)**: Codex-Innovation
- **Severity**: minor
- **Concern**: The planned `issue_close` wrapper does not specify how it canonicalizes the audited close forms that place `--repo` either before or after the issue identifier. Without an explicit accepted semantic form and ordering guarantee, sibling repointing may depend on undocumented `gh` argument reordering.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: State that the wrapper intentionally canonicalizes all close calls to `issue` followed by optional flags, and verify that ordering with the supported `gh issue close` grammar; otherwise provide an API that preserves the required repository-before-issue form.

