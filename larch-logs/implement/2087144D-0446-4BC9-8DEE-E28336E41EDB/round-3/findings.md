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

### FINDING_2: Sparse-cone comparison logic is duplicated
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `sessionstart-health.sh` and `upgrade-larch.sh` duplicate marketplace sparse-cone comparison logic instead of sharing one helper with `lib-sparse-dirs.sh`, creating drift risk for future allowlist or normalization changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: Upgrade retention test contains unused helper mirrors
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `is_cache_shaped_root_for_test` and `single_cache_version_dir_for_test` are now dead code after tests switched to sourcing the production resolver, adding harness noise.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

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

### FINDING_8: [OUT_OF_SCOPE] Missing sparse library can exit the caller shell when sourced
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-release-state-output.txt, dyn-sparse-cone-output.txt
- **Severity**: latent
- **Concern**: The missing `lib-sparse-dirs.sh` path uses `exit 1` before the sourced guard. If `upgrade-larch.sh` is sourced from release code in that state, it can terminate the orchestrator shell instead of returning an error.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From dyn-release-state-output.txt: Address the concern above.
  - From dyn-sparse-cone-output.txt: Address the concern above.

### FINDING_9: Release Step 7/8 state machine lacks direct harness coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-harness-hermeticity-output.txt
- **Severity**: important
- **Concern**: CI tests helpers and stubs rather than the actual SKILL Step 7/8 parsing flow. Real upgrade output, root resolution, capture, and release flag parsing are not validated together, so drift can ship without lint failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From dyn-harness-hermeticity-output.txt: Address the concern above.

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

### FINDING_12: `lib-quiet.sh` is still sourced from the active cache
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-sparse-cone-output.txt
- **Severity**: latent
- **Concern**: Sparse policy is sourced from `SCRIPT_ROOT`, but `lib-quiet.sh` still comes from `PLUGIN_ROOT` / active cache. A stale or tampered cache helper can run before reinstall refreshes the tree, splitting policy and operational helper sources.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From dyn-sparse-cone-output.txt: Address the concern above.

### FINDING_13: Cache root validation lacks canonicalization
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `is_cache_shaped_larch_root` checks prefix and basename only. A symlink under the cache version dir can pass validation while later file operations follow the symlink outside the cache parent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_14: Release machine-flag parsing can be spoofed by unanchored output text
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Step 7 parses `LARCH_*=true` via substring over captured upgrade output, so unrelated or spoofed CLI text could force unnecessary restart instructions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] Stall sentinel text is interpolated into SessionStart advisory context
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Crafted `larch-stalled-run.txt` fields can influence SessionStart advisory JSON context before `jq --arg`; reviewer marked this pre-existing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_16: Cone-only reconcile does not consistently emit restart-required signal
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-bash-runtime-output.txt
- **Severity**: latent
- **Concern**: A successful same-version cone repair emits `LARCH_CONE_RECONCILED=true` but not always `LARCH_RESTART_REQUIRED=true`, so automation watching only the canonical restart flag can miss the required restart.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-bash-runtime-output.txt: Address the concern above.

### FINDING_17: SessionStart sparse-cone drift probe is unnecessarily gated on jq
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Sparse-cone drift detection only needs git, but it runs inside a `jq && git` gate. Hosts with git but no jq miss cone-drift warnings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] gh-unavailable path reinstalls instead of taking idempotent cone-ok path
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-sparse-cone-output.txt
- **Severity**: latent
- **Concern**: When `gh` is unavailable, `already_latest_and_cone_ok` cannot run and the script falls through to unconditional reinstall even if version and cone already match.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-sparse-cone-output.txt: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] Skill-tool fallback can run stale installed upgrade code
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: If no cache root resolves, the release fallback may invoke the installed `/upgrade-larch` skill, which can lag the working tree in dev or no-marketplace-install scenarios.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_20: [OUT_OF_SCOPE] HOME-less root resolution remains unguarded in pre-existing paths
- **Reviewer(s)**: dyn-bash-runtime-output.txt
- **Severity**: nit
- **Concern**: `get_installed_larch_version` and `resolve_release_step7_root` still dereference `$HOME/.claude/...` without an empty-HOME guard; reviewer marked this as pre-existing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-runtime-output.txt: Address the concern above.

### FINDING_21: [OUT_OF_SCOPE] SessionStart drift probe requires jq despite git being enough
- **Reviewer(s)**: dyn-bash-runtime-output.txt
- **Severity**: latent
- **Concern**: A host with git but no jq receives no sparse-drift warning; reviewer marked this outside that review’s scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-runtime-output.txt: Address the concern above.

### FINDING_22: [OUT_OF_SCOPE] Sparse-checkout comparison algorithm may be sensitive to git output drift
- **Reviewer(s)**: dyn-bash-runtime-output.txt
- **Severity**: latent
- **Concern**: The `git sparse-checkout list` versus `normalize_sparse_dirs` equality algorithm is unchanged but now exercised more often, so git output-format drift could surface more often.
- **Suggested revisions (informational for voters; coder decides)**:
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

### FINDING_26: [OUT_OF_SCOPE] Skill-tool fallback branch is comment-only in the Bash fence
- **Reviewer(s)**: dyn-release-state-output.txt
- **Severity**: latent
- **Concern**: The fallback branch lacks mechanical in-repo capture/parse of fallback output; reviewer marked dependency on external orchestrator discipline as out of scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-release-state-output.txt: Address the concern above.

### FINDING_27: [OUT_OF_SCOPE] Source-side-effect tests do not assert fd or quiet env cleanliness
- **Reviewer(s)**: dyn-release-state-output.txt
- **Severity**: nit
- **Concern**: Tests assert sourcing avoids the production `ERR` trap, but do not assert fd 2 or `LARCH_QUIET_*` state remains unchanged.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-release-state-output.txt: Address the concern above.

### FINDING_28: [OUT_OF_SCOPE] Allowlist prose copies remain manually synchronized
- **Reviewer(s)**: dyn-sparse-cone-output.txt
- **Severity**: latent
- **Concern**: `lib-sparse-dirs.sh` centralizes the allowlist, but docs and test literals still contain manually synced copies; reviewer marked this as pre-existing/acknowledged.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-sparse-cone-output.txt: Address the concern above.

### FINDING_29: SessionStart sparse probe does not disable nounset while sourcing helper code
- **Reviewer(s)**: dyn-hook-failopen-output.txt
- **Severity**: important
- **Concern**: `probe_sparse_cone_drift()` disables `errexit` but not `nounset` under `set -euo pipefail`. A malformed or future helper touching an unset variable can abort SessionStart before its unconditional fail-open exit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-hook-failopen-output.txt: Address the concern above.

### FINDING_30: SessionStart drift compare assumes sed and sort exist
- **Reviewer(s)**: dyn-hook-failopen-output.txt
- **Severity**: latent
- **Concern**: The new sparse drift compare uses `sed` and `sort` without PATH guards. In stripped PATHs, this can produce repeated false advisories even if the hook exits successfully.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-hook-failopen-output.txt: Address the concern above.

### FINDING_31: [OUT_OF_SCOPE] Existing SessionStart git probes also assume common external tools
- **Reviewer(s)**: dyn-hook-failopen-output.txt
- **Severity**: latent
- **Concern**: Pre-existing git-state probes in the same block already rely on `sed` / `sort` / `awk` / `grep` without PATH guards; reviewer marked this as outside the new probe’s in-scope issue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-hook-failopen-output.txt: Address the concern above.

### FINDING_32: [OUT_OF_SCOPE] SessionStart test PATH does not exercise stripped sed/sort behavior
- **Reviewer(s)**: dyn-hook-failopen-output.txt
- **Severity**: nit
- **Concern**: `test-sessionstart-health.sh` links `sed`, `sort`, and `tr` into the test PATH, so it does not cover stripped-PATH skip/false-positive behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-hook-failopen-output.txt: Address the concern above.

### FINDING_33: [OUT_OF_SCOPE] Release Step 7 lacks prose fallback relative to SessionStart review scope
- **Reviewer(s)**: dyn-hook-failopen-output.txt
- **Severity**: latent
- **Concern**: Step 7 parses only `LARCH_CONE_RECONCILED=true` and lacks the planned reconcile-fragment fallback; reviewer marked this as outside the SessionStart fail-open surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-hook-failopen-output.txt: Address the concern above.

### FINDING_34: Production upgrade-output harness aborts on non-zero script exit
- **Reviewer(s)**: dyn-harness-hermeticity-output.txt
- **Severity**: latent
- **Concern**: Production-path tests capture `bash "$UPGRADE_SCRIPT" 2>&1` under `set -euo pipefail` without preserving `upgrade_rc`, so a non-zero upgrade aborts the harness and skips explicit assertions and PATH restoration.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-hermeticity-output.txt: Address the concern above.

### FINDING_35: [OUT_OF_SCOPE] Unused root-resolution test helpers are dead code only
- **Reviewer(s)**: dyn-harness-hermeticity-output.txt
- **Severity**: nit
- **Concern**: The retention test’s unused cache-shape helpers are dead code, but the reviewer marked them as not a hermeticity regression because production resolver coverage is used instead.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-hermeticity-output.txt: Address the concern above.
