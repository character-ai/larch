# Review Round 1

- Mode: `diff`
- 6 accepted, 3 rejected (2 exonerated)

## Accepted Findings

### FINDING_1: Notes-consuming Bash fences rely on lost shell state
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `.claude/skills/release/SKILL.md` documents re-deriving `NOTES_*` paths from `PR_LIST_FILE`, but later notes-consuming Bash fences still use `NOTES_FILE` / `REDACTED_NOTES_FILE` without rebinding them. Since Bash invocations do not share shell state, literal execution can use empty or stale paths for redact, PR body, or release notes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_10: Step 8 warning can tell users to switch to main when already on main
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Release Step 8 warning text always says to switch to `main` when `BRANCH_DELETED=false`, even after an ff-only pull failure where the operator is already on `main`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_11: Missing --branch error path is untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-shell-contracts-output.txt
- **Severity**: nit
- **Concern**: The local-cleanup harness does not test invocation without `--branch`, despite the documented contract requiring exit 1, empty stdout, and a specific stderr error.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From dyn-shell-contracts-output.txt: Address the concern above.


### FINDING_16: Recovery notes remain only in tmp storage
- **Reviewer(s)**: dyn-release-flow-output.txt
- **Severity**: latent
- **Concern**: Recovery guidance says to keep `NOTES_DIR`, but notes are under a `mktemp` directory with no durable-copy step. Delayed or multi-session recovery can lose `notes.redacted.md`, making Step 6 retry or promote-only recovery harder after remote release state has changed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-release-flow-output.txt: Address the concern above.


### FINDING_17: ff-only cleanup failure needs louder operator guidance
- **Reviewer(s)**: dyn-release-flow-output.txt
- **Severity**: latent
- **Concern**: After an ff-only pull failure, `/release` can still complete while local `main` may not contain the merged release commit and the local branch remains undeleted. The release cleanup docs and Step 8 warning do not clearly tell operators to manually reconcile before relying on the local tree.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-release-flow-output.txt: Address the concern above.

### FINDING_9: Common post-release cleanup success path lacks coverage
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `scripts/test-local-cleanup.sh` does not cover the common case where cleanup starts from the merged feature/release branch while local `main` is behind `origin/main` and should fast-forward, switch to `main`, delete the branch, and report success.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


