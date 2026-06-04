### FINDING_1: Notes-consuming Bash fences rely on lost shell state
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `.claude/skills/release/SKILL.md` documents re-deriving `NOTES_*` paths from `PR_LIST_FILE`, but later notes-consuming Bash fences still use `NOTES_FILE` / `REDACTED_NOTES_FILE` without rebinding them. Since Bash invocations do not share shell state, literal execution can use empty or stale paths for redact, PR body, or release notes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_2: Step 4 preview path is underspecified
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Step 4 preview / dry-run guidance does not clearly require re-resolving and previewing `REDACTED_NOTES_FILE`, so an operator or agent may preview the wrong notes file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_3: Step 8 duplicates ad hoc KV parsing
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Step 8 uses an ad hoc `awk` KV parser instead of the existing `kv_value` pattern or a shared helper, creating a second call site that can drift if the envelope format changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] local-cleanup header still describes generic pull
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-shell-contracts-output.txt
- **Severity**: nit
- **Concern**: `scripts/local-cleanup.sh` header prose says the helper “pulls the latest” even though the implementation and docs now specify `git pull --ff-only origin main`, which can mislead maintainers reading the script.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-shell-contracts-output.txt: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] ff-only pull argv coverage is too narrow
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, dyn-shell-contracts-output.txt
- **Severity**: nit
- **Concern**: The harness asserts `git pull --ff-only origin main` only in limited scenarios, so regressions back to merge-capable pull behavior may not be caught across other cleanup success or divergent-main paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From dyn-shell-contracts-output.txt: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] Change-bump path can reuse stale notes
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-release-flow-output.txt
- **Severity**: latent
- **Concern**: The Step 4 “Change bump” branch says to re-run prepare and re-confirm, but it does not explicitly require re-parsing the new prepare output, re-deriving `NOTES_*`, re-running compose/redact, and confirming from the new redacted notes. This can publish notes from an old temp dir or old bump window.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-release-flow-output.txt: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] implement NEVER #16 still says plain git pull
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-release-flow-output.txt, dyn-shell-contracts-output.txt
- **Severity**: nit
- **Concern**: `skills/implement/SKILL.md` NEVER #16 still references `git pull origin main` rather than `git pull --ff-only origin main`, creating documentation drift for implement cleanup behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-release-flow-output.txt: Address the concern above.
  - From dyn-shell-contracts-output.txt: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] implement-finalize can hide undeleted branch state
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `implement-finalize.sh` Step 14 success handling can ignore `BRANCH_DELETED=false` when `CLEANUP_SUCCESS=true`, potentially leaving a stale branch without a partial-warning signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_9: Common post-release cleanup success path lacks coverage
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `scripts/test-local-cleanup.sh` does not cover the common case where cleanup starts from the merged feature/release branch while local `main` is behind `origin/main` and should fast-forward, switch to `main`, delete the branch, and report success.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

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

### FINDING_12: [OUT_OF_SCOPE] local-cleanup accepts arbitrary branch-name strings
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `scripts/local-cleanup.sh` only rejects `--branch main` and does not validate that the supplied branch name is ref-safe, which is a broader pre-existing hardening gap for callers passing arbitrary feature branch names.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] reset-hard cleanup path can drop local flush-only commits
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: The pre-existing `git reset --hard origin/main` path can drop local flush-only commits when its predicates match, relying on trust in fetched `origin/main`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] fetch failure can leave origin/main stale before successful cleanup
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-release-flow-output.txt
- **Severity**: latent
- **Concern**: `local-cleanup.sh` continues after fetch failure; if subsequent pull behavior also relies on stale `origin/main`, cleanup can report success and delete the release branch even though local `main` did not actually catch up to the merged release commit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-release-flow-output.txt: Address the concern above.

### FINDING_15: Steps 7-8 are not explicitly gated on successful release-finish completion
- **Reviewer(s)**: dyn-release-flow-output.txt
- **Severity**: latent
- **Concern**: Release Steps 7-8 can be read as continuing after Step 6 publication even when `release-finish.sh` partially failed during Latest promotion. Continuing into cleanup after a partial Step 6 can delete the local release branch while promote-only recovery is still pending.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-release-flow-output.txt: Address the concern above.

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
