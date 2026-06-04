### FINDING_1: Release Step 7 sources the executable upgrade script and inherits side effects
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-bash-runtime-output.txt, dyn-release-state-output.txt, dyn-sparse-cone-output.txt
- **Severity**: important
- **Concern**: `/release` Step 7 sources `upgrade-larch.sh` only to call `resolve_release_step7_root`, but the script runs quiet logging setup, mutates fd/env/cache globals, and mixes release-only root resolution into the executable upgrade path before the sourced early-return. This can hide operator warnings, pollute later Step 7/8 state, and increase regression risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-bash-runtime-output.txt: Address the concern above.
  - From dyn-release-state-output.txt: Address the concern above.
  - From dyn-sparse-cone-output.txt: Address the concern above.


### FINDING_10: Root-resolution fallback can choose the wrong cache dir on version mismatch
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The sole-cache-dir fallback and its harness coverage do not adequately handle `CURRENT_VERSION` vs installed metadata mismatch. A retried release can resolve an old cache root and use wrong prune/stamp context.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_11: Already-latest harness does not assert absence of cone-reconcile flag
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The production already-latest test does not assert that `LARCH_CONE_RECONCILED` is absent, so a false-positive flag on the idempotent path could make release always demand restart.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_16: Cone-only reconcile does not consistently emit restart-required signal
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-bash-runtime-output.txt
- **Severity**: latent
- **Concern**: A successful same-version cone repair emits `LARCH_CONE_RECONCILED=true` but not always `LARCH_RESTART_REQUIRED=true`, so automation watching only the canonical restart flag can miss the required restart.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-bash-runtime-output.txt: Address the concern above.


### FINDING_23: Root-resolution errors are silenced into stale fallback behavior
- **Reviewer(s)**: dyn-release-state-output.txt
- **Severity**: important
- **Concern**: Step 7 calls `resolve_release_step7_root ... 2>/dev/null || true`, making metadata or `claude` failures indistinguishable from “no cache root” and pushing release into the stale Skill-tool fallback path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-release-state-output.txt: Address the concern above.


### FINDING_24: Step 8 restart guidance can be skipped if PR_LIST_FILE state is not carried forward
- **Reviewer(s)**: dyn-release-state-output.txt
- **Severity**: important
- **Concern**: Step 8 re-reads `release-step7.env` via `PR_LIST_FILE`, but early Step 8 fences do not require or restate that variable. If not carried forward, flags default false and restart guidance can be omitted after cone reconcile.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-release-state-output.txt: Address the concern above.


### FINDING_25: Release Step 7 depends on GitHub release-list freshness
- **Reviewer(s)**: dyn-release-state-output.txt
- **Severity**: important
- **Concern**: Step 7 runs immediately after promote/tag but `upgrade-larch.sh` discovers the target via `gh api` release listing. If GitHub lags, Step 7 can verify against stale data, fail, or leave restart/cone flags unset.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-release-state-output.txt: Address the concern above.


### FINDING_29: SessionStart sparse probe does not disable nounset while sourcing helper code
- **Reviewer(s)**: dyn-hook-failopen-output.txt
- **Severity**: important
- **Concern**: `probe_sparse_cone_drift()` disables `errexit` but not `nounset` under `set -euo pipefail`. A malformed or future helper touching an unset variable can abort SessionStart before its unconditional fail-open exit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-hook-failopen-output.txt: Address the concern above.


### FINDING_3: Upgrade retention test contains unused helper mirrors
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `is_cache_shaped_root_for_test` and `single_cache_version_dir_for_test` are now dead code after tests switched to sourcing the production resolver, adding harness noise.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_34: Production upgrade-output harness aborts on non-zero script exit
- **Reviewer(s)**: dyn-harness-hermeticity-output.txt
- **Severity**: latent
- **Concern**: Production-path tests capture `bash "$UPGRADE_SCRIPT" 2>&1` under `set -euo pipefail` without preserving `upgrade_rc`, so a non-zero upgrade aborts the harness and skips explicit assertions and PATH restoration.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-hermeticity-output.txt: Address the concern above.


### FINDING_4: Cone repair can exit successfully without fail-closed handling when post-check still mismatches
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-sparse-cone-output.txt
- **Severity**: important
- **Concern**: `LARCH_CONE_RECONCILED=true` is emitted only if the post-install sparse-cone comparison passes. If reinstall ran but the cone still mismatches or comparison false-negatives, release automation may see exit 0 with no reconcile signal and skip the restart despite the attempted repair.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-sparse-cone-output.txt: Address the concern above.


### FINDING_5: Release Step 7 drops machine flags when upgrade exits non-zero
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-runtime-output.txt
- **Severity**: important
- **Concern**: Step 7 parses `LARCH_CONE_RECONCILED` / related flags only on `upgrade_rc=0`, but `upgrade-larch.sh` can emit a reconcile signal before a later verification failure exits non-zero. Step 8 then sees `CONE_RECONCILED=false` and may omit a required restart.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-bash-runtime-output.txt: Address the concern above.


### FINDING_6: Release and tests omit the planned reconcile prose fallback
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-harness-hermeticity-output.txt
- **Severity**: latent
- **Concern**: Step 7 and its tests only accept the machine line for cone reconciliation and reject/omit the planned fixed prose-fragment fallback. A successful reinstall that prints the reconcile banner but misses the machine line leaves `CONE_RECONCILED=false`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-harness-hermeticity-output.txt: Address the concern above.


### FINDING_7: Cache-shaped root checks use unguarded HOME
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `is_cache_shaped_larch_root` uses `$HOME` in cache path checks without guarding empty `HOME`, which can make root resolution probe wrong paths in stripped environments.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_9: Release Step 7/8 state machine lacks direct harness coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-harness-hermeticity-output.txt
- **Severity**: important
- **Concern**: CI tests helpers and stubs rather than the actual SKILL Step 7/8 parsing flow. Real upgrade output, root resolution, capture, and release flag parsing are not validated together, so drift can ship without lint failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From dyn-harness-hermeticity-output.txt: Address the concern above.


