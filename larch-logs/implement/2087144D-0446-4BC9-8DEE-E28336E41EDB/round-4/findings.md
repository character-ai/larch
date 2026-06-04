### FINDING_1: Untracked release-step7-root.sh breaks clean release/test runs
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-bash32-output.txt, dyn-sparse-cone-output.txt, dyn-harness-env-output.txt
- **Severity**: important
- **Concern**: `skills/upgrade-larch/scripts/release-step7-root.sh` is referenced by release Step 7 and tests but is absent from the tracked branch, so clean checkouts/CI can fail when sourcing it. The shipped helper also needs any required sibling contract/lint wiring.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-bash32-output.txt, dyn-sparse-cone-output.txt, dyn-harness-env-output.txt: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] Duplicate root-resolution helpers can drift
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash32-output.txt, dyn-release-state-output.txt, dyn-sparse-cone-output.txt
- **Severity**: important
- **Concern**: `upgrade-larch.sh` duplicates root-resolution/version helper logic that release/tests intend to consume from `release-step7-root.sh`, creating two authorities that can diverge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash32-output.txt, dyn-release-state-output.txt, dyn-sparse-cone-output.txt: Address the concern above.

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

### FINDING_10: release-step7.env write/read contract lacks regression coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: There is no automated test covering release Step 7 env persistence and Step 8 readback, so prompt-side drift could silently drop restart guidance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_11: LARCH_EXPECTED_STABLE_VERSION override lacks test/trust-boundary hardening
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: The expected-stable override can bypass GitHub stable-release verification and its release-only coupling is not covered by harnesses or clearly bounded for non-release callers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] SessionStart stall sentinel text may be injectable
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Pre-existing stall sentinel fields are interpolated into hook context before `jq --arg`, which could influence SessionStart context if an attacker can write the sentinel file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] Cache-root prefix validation lacks realpath hardening
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `is_cache_shaped_larch_root` uses prefix matching without canonicalizing `CLAUDE_PLUGIN_ROOT`, leaving a symlink-hardening concern under the cache trust model.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] Metadata cache miss prevents planned fallback root resolution
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-release-state-output.txt, dyn-cache-prune-output.txt
- **Severity**: important
- **Concern**: When installed metadata names a version but that cache dir is missing, `release-step7-root.sh` returns failure instead of falling through to `CURRENT_VERSION`, sole-cache, or expected-version fallbacks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-release-state-output.txt, dyn-cache-prune-output.txt: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] get_installed_larch_version does not guard HOME
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `get_installed_larch_version` can read an unintended installed-plugins path when `HOME` is empty in a stripped environment.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] SessionStart pipefail behavior was reviewed as non-defective
- **Reviewer(s)**: dyn-bash32-output.txt
- **Severity**: nit
- **Concern**: `probe_sparse_cone_drift()` does not disable `pipefail`, but the reviewer classified this as matching the hook’s fail-open posture rather than a new defect.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash32-output.txt: Address the concern above.

### FINDING_17: release-step7.env write path is unsafe when PR_LIST_FILE is missing
- **Reviewer(s)**: dyn-release-state-output.txt
- **Severity**: important
- **Concern**: Release Step 7 computes `PREPARE_DIR="$(dirname "$PR_LIST_FILE")"` without guarding `PR_LIST_FILE`; if empty, state can be written to `.` and Step 8 will not read it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-release-state-output.txt: Address the concern above.

### FINDING_18: Manual /upgrade-larch can still use stale cached script during release window
- **Reviewer(s)**: dyn-sparse-cone-output.txt
- **Severity**: important
- **Concern**: `/release` runs the working-tree upgrade script, but the operator-facing `/upgrade-larch` skill still uses `${CLAUDE_PLUGIN_ROOT}`, so pre-restart manual upgrades can execute stale cached sparse-dir logic.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-sparse-cone-output.txt: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] SessionStart allowlist check intentionally uses loaded plugin
- **Reviewer(s)**: dyn-sparse-cone-output.txt
- **Severity**: nit
- **Concern**: SessionStart drift probing loads `lib-sparse-dirs.sh` from the loaded plugin rather than a working tree, so it cannot see newer allowlists until restart; reviewer marked this as a documented trade-off.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-sparse-cone-output.txt: Address the concern above.

### FINDING_20: [OUT_OF_SCOPE] Sparse allowlist prose copies remain scattered
- **Reviewer(s)**: dyn-sparse-cone-output.txt
- **Severity**: nit
- **Concern**: Several docs still contain manual prose copies of the sparse allowlist, preserving edit-in-sync risk outside the main library/test guard.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-sparse-cone-output.txt: Address the concern above.

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

### FINDING_24: [OUT_OF_SCOPE] SessionStart 4g assertion does not fully prove PLUGIN_ROOT is ignored
- **Reviewer(s)**: dyn-harness-env-output.txt
- **Severity**: nit
- **Concern**: Case `4g` verifies an advisory appears but does not falsify accidental `CLAUDE_PLUGIN_ROOT` reads; reviewer marked this as weaker than the plan but not a main regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-env-output.txt: Address the concern above.

### FINDING_25: [OUT_OF_SCOPE] Harness hermeticity improvements noted as otherwise solid
- **Reviewer(s)**: dyn-harness-env-output.txt
- **Severity**: nit
- **Concern**: Reviewer noted the diff’s hermeticity improvements were otherwise solid and did not identify an additional defect in that observation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-env-output.txt: Address the concern above.
