### FINDING_1: Case 9 does not exercise git-to-find fallback parity
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Harness case 9 is labeled as git fallback parity but only runs in a never-git temp directory, so divergence between `git ls-files` and `find` after removing `.git` would not be caught.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_2: Git enumeration lacks positive violation coverage
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: The git enumeration branch is only tested for `larch-logs` exclusion, not for detecting a tracked bad shell file outside `larch-logs`, so regressions that skip normal tracked paths could pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: `agent-lint.toml` change is undocumented against plan
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `agent-lint.toml` was changed despite the plan saying no changes or omitting it from the planned file list; reviewers ask for the plan/docs/PR note to reflect the intentional lint exclude change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_4: `list_shell_files` name no longer matches target set
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `list_shell_files` also lists Python files, making the function name misleading for future readers or extenders.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: EOL or multiline `--body` usage can bypass detection
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The `--body[^-]` matcher requires a character after `--body`, so bare `--body` at end of line or split/continued forms may be missed; the harness also lacks a negative test locking the intended bare-EOL non-match behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_6: Trailing comments can cause false positives
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: The linter does not strip trailing shell comments before matching, so a safe `--body-file` command followed by a comment mentioning `--body` can be falsely flagged.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_7: Python single-quoted argv-list form is untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The plan/docs require Python single-quoted `['gh', ...]` argv-list detection, but the harness only covers the double-quoted form, so regex regressions for single quotes would pass CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_8: GNU `--body=foo` form is untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The documented forbidden `--body=foo` form has no harness coverage, so regex changes could stop flagging it without failing CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_9: Untracked git-worktree violations are untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: There is no harness case confirming inline `gh --body` in an untracked shell file inside a git worktree is detected before `git add`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] Aggregate lint does not include `lint-gh-body-inline`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `make lint` includes other new lints but not `lint-gh-body-inline`; reviewer marks this plan-intentional and suggests only an optional docs note if confusing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_11: Allow-comment suppression is too broad
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The `lint-gh-body-inline: ok` suppressor matches anywhere on a line, including strings or pre-command assignments, allowing an inline `gh --body` command to bypass the lint without a trailing pragma comment.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] Existing `lint-bash32` suppression has same loose pattern
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The pre-existing `lint-bash32` suppressor uses the same broad substring pattern; reviewer marks this as inherited sibling behavior for separate hardening.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] Branch includes unrelated commits
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: The reviewed branch includes unrelated commits beyond `178a3f95`, so whole-branch plan-fidelity review may conflate separate work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] Plan acceptance mentions nonexistent third stub assertion
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: The plan cites three stub-assertion annotations, but the repo only needs two, creating acceptance-checklist ambiguity rather than an implementation defect.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
