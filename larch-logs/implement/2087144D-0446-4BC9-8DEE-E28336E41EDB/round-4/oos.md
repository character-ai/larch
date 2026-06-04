### FINDING_12: [OUT_OF_SCOPE] SessionStart stall sentinel text may be injectable
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Pre-existing stall sentinel fields are interpolated into hook context before `jq --arg`, which could influence SessionStart context if an attacker can write the sentinel file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### FINDING_13: [OUT_OF_SCOPE] Cache-root prefix validation lacks realpath hardening
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `is_cache_shaped_larch_root` uses prefix matching without canonicalizing `CLAUDE_PLUGIN_ROOT`, leaving a symlink-hardening concern under the cache trust model.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_14: [OUT_OF_SCOPE] Metadata cache miss prevents planned fallback root resolution
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-release-state-output.txt, dyn-cache-prune-output.txt
- **Severity**: important
- **Concern**: When installed metadata names a version but that cache dir is missing, `release-step7-root.sh` returns failure instead of falling through to `CURRENT_VERSION`, sole-cache, or expected-version fallbacks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-release-state-output.txt, dyn-cache-prune-output.txt: Address the concern above.


Vote tally: YES=2 NO=1 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_15: [OUT_OF_SCOPE] get_installed_larch_version does not guard HOME
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `get_installed_larch_version` can read an unintended installed-plugins path when `HOME` is empty in a stripped environment.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_16: [OUT_OF_SCOPE] SessionStart pipefail behavior was reviewed as non-defective
- **Reviewer(s)**: dyn-bash32-output.txt
- **Severity**: nit
- **Concern**: `probe_sparse_cone_drift()` does not disable `pipefail`, but the reviewer classified this as matching the hook’s fail-open posture rather than a new defect.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash32-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_19: [OUT_OF_SCOPE] SessionStart allowlist check intentionally uses loaded plugin
- **Reviewer(s)**: dyn-sparse-cone-output.txt
- **Severity**: nit
- **Concern**: SessionStart drift probing loads `lib-sparse-dirs.sh` from the loaded plugin rather than a working tree, so it cannot see newer allowlists until restart; reviewer marked this as a documented trade-off.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-sparse-cone-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_2: [OUT_OF_SCOPE] Duplicate root-resolution helpers can drift
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash32-output.txt, dyn-release-state-output.txt, dyn-sparse-cone-output.txt
- **Severity**: important
- **Concern**: `upgrade-larch.sh` duplicates root-resolution/version helper logic that release/tests intend to consume from `release-step7-root.sh`, creating two authorities that can diverge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash32-output.txt, dyn-release-state-output.txt, dyn-sparse-cone-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_20: [OUT_OF_SCOPE] Sparse allowlist prose copies remain scattered
- **Reviewer(s)**: dyn-sparse-cone-output.txt
- **Severity**: nit
- **Concern**: Several docs still contain manual prose copies of the sparse allowlist, preserving edit-in-sync risk outside the main library/test guard.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-sparse-cone-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_24: [OUT_OF_SCOPE] SessionStart 4g assertion does not fully prove PLUGIN_ROOT is ignored
- **Reviewer(s)**: dyn-harness-env-output.txt
- **Severity**: nit
- **Concern**: Case `4g` verifies an advisory appears but does not falsify accidental `CLAUDE_PLUGIN_ROOT` reads; reviewer marked this as weaker than the plan but not a main regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-env-output.txt: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### FINDING_25: [OUT_OF_SCOPE] Harness hermeticity improvements noted as otherwise solid
- **Reviewer(s)**: dyn-harness-env-output.txt
- **Severity**: nit
- **Concern**: Reviewer noted the diff’s hermeticity improvements were otherwise solid and did not identify an additional defect in that observation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-env-output.txt: Address the concern above.

Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

