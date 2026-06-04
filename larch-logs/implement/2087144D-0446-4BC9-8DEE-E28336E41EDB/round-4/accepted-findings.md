### FINDING_1: Untracked release-step7-root.sh breaks clean release/test runs
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-bash32-output.txt, dyn-sparse-cone-output.txt, dyn-harness-env-output.txt
- **Severity**: important
- **Concern**: `skills/upgrade-larch/scripts/release-step7-root.sh` is referenced by release Step 7 and tests but is absent from the tracked branch, so clean checkouts/CI can fail when sourcing it. The shipped helper also needs any required sibling contract/lint wiring.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-bash32-output.txt, dyn-sparse-cone-output.txt, dyn-harness-env-output.txt: Address the concern above.


### FINDING_10: release-step7.env write/read contract lacks regression coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: There is no automated test covering release Step 7 env persistence and Step 8 readback, so prompt-side drift could silently drop restart guidance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_17: release-step7.env write path is unsafe when PR_LIST_FILE is missing
- **Reviewer(s)**: dyn-release-state-output.txt
- **Severity**: important
- **Concern**: Release Step 7 computes `PREPARE_DIR="$(dirname "$PR_LIST_FILE")"` without guarding `PR_LIST_FILE`; if empty, state can be written to `.` and Step 8 will not read it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-release-state-output.txt: Address the concern above.


### FINDING_21: already-latest early exit ignores active cache-root version mismatch
- **Reviewer(s)**: dyn-cache-prune-output.txt
- **Severity**: important
- **Concern**: `already_latest_and_cone_ok()` compares metadata to latest stable and cone state but not the active cache root basename, so release can early-exit while the active cache still points at an older version missing new allowlisted paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cache-prune-output.txt: Address the concern above.


### FINDING_22: Production harness PATH stubs can leak after assertion failure
- **Reviewer(s)**: dyn-harness-env-output.txt
- **Severity**: important
- **Concern**: Production integration cases prepend stub `gh`/`claude` directories to `PATH` and restore only after successful assertions, so `set -e` failures can pollute later cases.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-env-output.txt: Address the concern above.


### FINDING_23: SessionStart sparse-cone harness duplicates expected allowlist
- **Reviewer(s)**: dyn-harness-env-output.txt
- **Severity**: important
- **Concern**: `scripts/test-sessionstart-health.sh` hard-codes expected sparse dirs independently from `scripts/lib-sparse-dirs.sh`, allowing allowlist edits to drift across harnesses.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-env-output.txt: Address the concern above.


### FINDING_3: Cone-reconciled success token is emitted before verified repair
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash32-output.txt, dyn-release-state-output.txt, dyn-cache-prune-output.txt
- **Severity**: important
- **Concern**: `LARCH_CONE_RECONCILED=true` is emitted whenever reconcile was attempted or pre-run drift was detected, even if post-reinstall sparse-cone verification fails or the upgrade exits non-zero.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash32-output.txt, dyn-release-state-output.txt, dyn-cache-prune-output.txt: Address the concern above.


### FINDING_4: upgrade-larch contract docs disagree with reconcile-token behavior
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-release-state-output.txt
- **Severity**: important
- **Concern**: `upgrade-larch.md` claims reconcile/restart signals are success-gated, while current script/release behavior can emit or parse them before final verification.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-release-state-output.txt: Address the concern above.


### FINDING_5: upgrade-larch SKILL.md documents the wrong release helper root
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `skills/upgrade-larch/SKILL.md` says release sources `release-step7-root.sh` from `CLAUDE_PLUGIN_ROOT`, conflicting with the working-tree path used by release Step 7.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_6: Sparse-dir library docs omit release-step7-root.sh as a consumer
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/lib-sparse-dirs.md` does not list `release-step7-root.sh` as a consumer/edit-in-sync surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_7: Release Step 7 persists CONE_RECONCILED from ungated output/prose
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash32-output.txt, dyn-release-state-output.txt
- **Severity**: important
- **Concern**: Release Step 7 sets `CONE_RECONCILED`/restart state from captured output, including an early prose banner, without requiring `upgrade_rc=0` or a verified post-success machine signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash32-output.txt, dyn-release-state-output.txt: Address the concern above.


### FINDING_8: Retention harness encodes false-positive failed-upgrade flags
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `test-upgrade-larch-retention.sh` currently expects `CONE_RECONCILED`/`RESTART_REQUIRED` to survive failed upgrade output, so success-gating fixes will require test updates.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_9: No harness asserts NEW_VERSION_INSTALLED on verified version bump
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Production-style upgrade tests do not verify that a successful version bump emits `LARCH_NEW_VERSION_INSTALLED=true`, risking release Step 8 restart omissions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


