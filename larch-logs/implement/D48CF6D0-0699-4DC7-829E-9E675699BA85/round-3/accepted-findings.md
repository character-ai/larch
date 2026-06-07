### FINDING_1: Auto-fix dirty checks use plugin root instead of consumer repo
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-correctness-output.txt, dyn-bash-flow-output.txt, dyn-vendor-fix-output.txt, dyn-workflow-contract-output.txt
- **Severity**: important
- **Concern**: `/design` auto-fix passes the plugin root as `--repo-root`, so dirty-tree and Tier 3 validation checks can miss mutations in the consumer repository where `/design` is actually running.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, cursor-specialist-correctness-output.txt, dyn-bash-flow-output.txt, dyn-vendor-fix-output.txt, dyn-workflow-contract-output.txt: Address the concern above.


### FINDING_11: Revert loses cumulative accepted OOS artifacts
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `revert-round` restores `oos-accepted-design.md` from a per-round snapshot rather than a cumulative prior state, so reverting a later round can drop earlier accepted OOS findings before filing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_12: Tmpdir side mutation can force unnecessary auto-fix exhaustion
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: If a vendor fixes the target plan but also touches a non-target tmpdir artifact, the guard marks the attempt failed without revalidating the now-fixed plan, causing avoidable operator escalation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_13: Optional trailer snapshot is stale across auto-fix attempts
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Optional-trailer snapshot/dedup state is captured once before the loop rather than per attempt, so a corrupted target from an earlier attempt can poison later dedup or size metadata handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_14: Revert does not clear Gate B post-apply sentinel
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-bash-flow-output.txt
- **Severity**: latent
- **Concern**: `revert-round` clears many downstream markers but not `.completed/step-2b.5`, leaving pause/resume state claiming post-apply settlement completed for a round whose plan was reverted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, dyn-bash-flow-output.txt: Address the concern above.


### FINDING_15: Step 3 prose still describes Gate B as operator-approved
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-bash-flow-output.txt, dyn-workflow-contract-output.txt
- **Severity**: nit
- **Concern**: Step 3 branch-matrix wording still calls Gate B the sole operator-approved apply point, conflicting with the new default auto-apply / `--approve` opt-in contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, dyn-bash-flow-output.txt, dyn-workflow-contract-output.txt: Address the concern above.


### FINDING_16: Repo dirty guard misses content changes with unchanged porcelain status
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The repo guard compares only `git status --porcelain`, so edits to already-dirty or existing untracked files can leave the before/after status text unchanged and evade detection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt: Address the concern above.


### FINDING_17: Assessor Revert prompt branch lacks runtime harness coverage
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Assessor tests stop before exercising the new Revert prompt branch, so SKILL wiring bugs around restore, warnings, rollback state, or markers can pass CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_18: Pause during Gate B auto-apply can double-apply findings
- **Reviewer(s)**: dyn-bash-flow-output.txt
- **Severity**: important
- **Concern**: A pause after Step 3 but before `.completed/step-3.5` is written resumes into Gate B and can re-run default Apply-all with no idempotency guard, silently applying the same findings twice.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-flow-output.txt: Address the concern above.


### FINDING_19: Resume and already-planned paths can ignore current `--approve`
- **Reviewer(s)**: dyn-state-io-output.txt
- **Severity**: important
- **Concern**: Resume and already-planned paths can bypass `run-params.json` refresh/merge, so an operator invoking `/design --approve` may still resume into silent auto-apply if the restored params omit or set `approve_requested:false`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-io-output.txt: Address the concern above.


### FINDING_23: Auto-fix vendor selection ignores availability flags
- **Reviewer(s)**: dyn-vendor-fix-output.txt
- **Severity**: latent
- **Concern**: Auto-fix chooses vendors from `CODEX_PRESENT` / `CURSOR_PRESENT` instead of the degraded-tools availability flags, so it can dispatch tools the rest of `/design` already treats as unavailable.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-vendor-fix-output.txt: Address the concern above.


### FINDING_24: Auto-fix integrity harness lacks dirty-tree and rollback coverage
- **Reviewer(s)**: dyn-vendor-fix-output.txt
- **Severity**: latent
- **Concern**: Existing auto-fix tests do not cover repo dirty-tree detection or target-file rollback after guard failure, leaving the main integrity controls without regression coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-vendor-fix-output.txt: Address the concern above.


### FINDING_26: py-lint relevant-checks behavior is inconsistent with Python 3.11 floor
- **Reviewer(s)**: dyn-ci-pycompat-output.txt
- **Severity**: important
- **Concern**: `relevant-checks.sh` can append `py-lint` when lint tools are present without first probing Python ≥3.11, while `make py-lint` now enforces that floor; docs also omit the py-lint version gate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-pycompat-output.txt: Address the concern above.


### FINDING_4: Failed auto-fix attempts leave target plan mutations behind
- **Reviewer(s)**: cursor-specialist-security-output.txt, codex-specialist-security-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-vendor-fix-output.txt
- **Severity**: important
- **Concern**: Failed, guarded, or exhausted auto-fix attempts can leave unvalidated vendor edits in `plan.txt`/`composed-plan.md`, so later retries or operator override may proceed from a corrupted or unapproved plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, codex-specialist-security-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-vendor-fix-output.txt: Address the concern above.


### FINDING_6: Tmpdir guard and restore are not symlink-safe or fail-closed
- **Reviewer(s)**: codex-specialist-security-output.txt, cursor-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, dyn-vendor-fix-output.txt
- **Severity**: important
- **Concern**: The tmpdir mutation guard misses symlinks/non-regular entries, only checks the target before dispatch, and can ignore restore failures, allowing unsafe entries or half-restored state to survive into later validation or retries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-security-output.txt, cursor-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, dyn-vendor-fix-output.txt: Address the concern above.


### FINDING_8: Gate B auto-apply regression coverage is incomplete
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Required or relevant harnesses do not fully exercise default auto-apply, `--approve` prompt behavior, cap/bypass paths, or actual Apply-all plan rewriting, so Gate B regressions can pass CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt: Address the concern above.


