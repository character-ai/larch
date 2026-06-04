### FINDING_11: [OUT_OF_SCOPE] Cached `/upgrade-larch` entrypoint cannot bootstrap fixes from a pre-fix cache
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-sparse-rooting-output.txt
- **Severity**: latent
- **Concern**: The `/upgrade-larch` skill runs the cached script under `CLAUDE_PLUGIN_ROOT`, so broken pre-fix caches may continue running old logic until a release working-tree invocation or version bump installs the new script and library.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, dyn-sparse-rooting-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_12: [OUT_OF_SCOPE] Installed-version metadata can disagree with `PLUGIN_ROOT` basename
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `get_installed_larch_version` can disagree with the active cache-root basename, creating ambiguity between metadata-driven idempotency and `PLUGIN_ROOT`-based prune behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_16: [OUT_OF_SCOPE] Negative tests for failed reconcile signaling are absent
- **Reviewer(s)**: dyn-cli-signals-output.txt
- **Severity**: nit
- **Concern**: There is no harness case proving that failed verification with `upgrade_rc=1` cannot set `CONE_RECONCILED` through captured output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cli-signals-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_17: [OUT_OF_SCOPE] Release-tag propagation race can choose previous stable
- **Reviewer(s)**: dyn-release-flow-output.txt
- **Severity**: latent
- **Concern**: If GitHub releases do not surface the just-cut tag immediately after promotion, Step 7 may reconcile against the previous stable version rather than installing `NEW_VERSION`; this timing hazard predates the sparse-allowlist work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-release-flow-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_18: [OUT_OF_SCOPE] Intentional sparse-dir word splitting is pre-existing
- **Reviewer(s)**: dyn-sparse-git-output.txt
- **Severity**: nit
- **Concern**: The unquoted `--sparse $LARCH_SPARSE_DIRS` word splitting is intentionally shellcheck-suppressed for space-separated top-level tokens and is not a regression from this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-sparse-git-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_19: [OUT_OF_SCOPE] `gh`-unavailable unconditional reinstall behavior is longstanding
- **Reviewer(s)**: dyn-sparse-git-output.txt
- **Severity**: nit
- **Concern**: When `gh` cannot resolve `LATEST_STABLE`, `already_latest_and_cone_ok` cannot early-exit and may reinstall without the reconcile banner; this is documented longstanding behavior, not introduced here.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-sparse-git-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_20: [OUT_OF_SCOPE] Run-log churn is unrelated to sparse-cone logic
- **Reviewer(s)**: dyn-sparse-git-output.txt
- **Severity**: nit
- **Concern**: Commit `53bb3d6d6` only changes `larch-logs/` implement run-log files and is unrelated to the sparse-cone review surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-sparse-git-output.txt: Address the concern above.

Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

