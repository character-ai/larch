Normalized reviewer findings into a merged structured list. In-scope duplicates are consolidated; distinct code paths and out-of-scope observations are kept separate per the aggregator rules.
### FINDING_1: release-step7-root.sh untracked — breaks Step 7 and harness on clean checkout
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, dyn-sparse-install-output.txt
- **Severity**: important
- **Concern**: `skills/upgrade-larch/scripts/release-step7-root.sh` exists in the working tree but is untracked and absent from the committed branch diff. `.claude/skills/release/SKILL.md` Step 7 and `test-upgrade-larch-retention.sh` both `source` it. On a clean checkout, `/release` Step 7 fails at the `source` call and every root-resolution harness case aborts before assertions; `make test-upgrade-larch-retention` is broken for anyone pulling this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add and commit release-step7-root.sh (and sibling .md) before merge
  - From cursor-specialist-plan-fidelity-output.txt: Commit skills/upgrade-larch/scripts/release-step7-root.sh or repoint release/tests to a committed resolver.
  - From cursor-specialist-correctness-output.txt: `git add skills/upgrade-larch/scripts/release-step7-root.sh` and include it in the final commit for this branch.
  - From cursor-specialist-testing-output.txt: Stage and commit `skills/upgrade-larch/scripts/release-step7-root.sh` as part of this PR.
  - From cursor-specialist-security-output.txt: Commit `skills/upgrade-larch/scripts/release-step7-root.sh` (which the working tree already contains) as part of this PR; add it to `agent-lint.toml` excluded paths with the same sourced-library comment pattern used for other libs.
  - From dyn-sparse-install-output.txt: Stage and commit `skills/upgrade-larch/scripts/release-step7-root.sh` as part of this PR. Also add `skills/upgrade-larch/scripts/release-step7-root.md` (the required sibling contract per `script-md-siblings.md`) and add both to `agent-lint.toml`'s dead-script exclude list (the file has a shebang and is sourced-only, so agent-lint will flag it without an explicit exclusion).

### FINDING_2: Duplicate root-resolution helpers in upgrade-larch.sh
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-state-output.txt, dyn-sparse-install-output.txt
- **Severity**: important
- **Concern**: `resolve_release_step7_root` and related helpers (`is_cache_shaped_larch_root`, `single_larch_cache_version_dir`, and a scoped `get_installed_larch_version`) are duplicated in `upgrade-larch.sh` and `release-step7-root.sh` with already-diverging details (e.g. `release_step7_cache_parent()` vs direct `$HOME` binding; empty-`HOME` guard only in the standalone file). The `upgrade-larch.sh` copy is dead on the release path and can silently desync from the canonical implementation that release and the harness source.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Delete unused resolve_release_step7_root/single_larch_cache_version_dir/is_cache_shaped_larch_root from upgrade-larch.sh; source shared helpers from release-step7-root.sh only
  - From cursor-specialist-edge-cases-output.txt: Keep single copy in release-step7-root.sh
  - From cursor-specialist-plan-fidelity-output.txt: Single canonical release-step7-root.sh; source it from upgrade-larch.sh for is_cache_shaped only; remove unused duplicate.
  - From dyn-bash-state-output.txt: Delete the duplicate helpers from `upgrade-larch.sh` and keep `release-step7-root.sh` as the sole implementation, or source that file from a single shared location and test only the shared copy.
  - From dyn-sparse-install-output.txt: Remove `resolve_release_step7_root`, `is_cache_shaped_larch_root`, `single_larch_cache_version_dir`, and the `release-step7-root.sh`-scoped copy of `get_installed_larch_version` from `upgrade-larch.sh` entirely, leaving only the implementations in `release-step7-root.sh`. The sourcing guard (`if [[ "${BASH_SOURCE[0]}" != "${0}" ]]; then return 0; fi`) already prevents this from affecting direct upgrade execution. If `already_latest_and_cone_ok` in `upgrade-larch.sh` needs `is_cache_shaped_larch_root`, source `release-step7-root.sh` from `$SCRIPT_ROOT` or inline just that one small helper.

### FINDING_3: Missing release-step7-root.md sibling contract
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: New `release-step7-root.sh` has no co-located `release-step7-root.md` contract required by `script-md-siblings`. Contributors lack documented resolution ordering and invariants; `agent-lint` may flag the sourced-only script as dead code without an exclude entry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add release-step7-root.md and agent-lint exclude if sourced-only
  - From cursor-specialist-plan-fidelity-output.txt: Add release-step7-root.md documenting purpose callers and edit-in-sync.
  - From cursor-specialist-testing-output.txt: Add `skills/upgrade-larch/scripts/release-step7-root.md` as a sibling contract doc. If agent-lint flags it as a dead script, also add an exclude entry in `agent-lint.toml` with a sourced-only comment.

### FINDING_4: get_installed_larch_version duplicated with divergent failure handling
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `get_installed_larch_version` is duplicated in `upgrade-larch.sh` and `release-step7-root.sh` with different grep/`installed_plugins.json` failure handling. `/release` Step 7 and `/upgrade-larch` can disagree on whether installed metadata exists when `installed_plugins.json` is absent or malformed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract one shared get_installed_larch_version; source from both scripts

### FINDING_5: LARCH_EXPECTED_STABLE_VERSION undocumented in upgrade-larch contract
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `LARCH_EXPECTED_STABLE_VERSION`, used by `/release` Step 7 to pin stable resolution, is not documented in `upgrade-larch.md` along with the machine-readable stderr lines release automation parses.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Document LARCH_EXPECTED_STABLE_VERSION and machine-readable stderr lines in upgrade-larch.md

### FINDING_6: Sparse cone compare logic duplicated between SessionStart and upgrade-larch
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Sparse cone comparison logic is duplicated between `sessionstart-health.sh` and `upgrade-larch.sh`. Allowlist normalization changes may require two edits to keep warnings and reconciliation aligned.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add a shared compare helper to lib-sparse-dirs.sh

### FINDING_7: Test helpers duplicate release Step 7/8 flag parsing from SKILL.md
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `test-upgrade-larch-retention.sh` duplicates release Step 7/8 flag parsing and state-file logic from `release/SKILL.md`. Future release prompt edits can pass harness tests while diverging from actual orchestrator behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract shared helpers into release-step7-root.sh or a small release-step7-state module

### FINDING_8: Step 7 upgrade gated on PR_LIST_FILE presence
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Release Step 7 only runs the working-tree upgrade when `PR_LIST_FILE` is present. Missing or lost prepare artifacts skip the entire upgrade path, not just restart-state persistence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Run resolution and upgrade unconditionally; write release-step7.env only when PREPARE_DIR is known

### FINDING_9: Cone/restart machine lines withheld when stable verification fails
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-release-step7-output.txt
- **Severity**: important
- **Concern**: During `/release` Step 7, `LARCH_EXPECTED_STABLE_VERSION` always sets `LATEST_STABLE`. When post-reinstall stable verification fails (`VERIFIED_TARGET=false`), `upgrade-larch.sh` exits 1 and withholds `LARCH_CONE_RECONCILED=true` and/or `LARCH_RESTART_REQUIRED=true` even if the install was mutated or cone repair succeeded. Step 7 only records flags on `upgrade_rc -eq 0`, so Step 8 can finish without mandating restart despite changed marketplace/plugin state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Decouple cone-repair signals from VERIFIED_TARGET when post-reinstall cone matches
  - From cursor-specialist-plan-fidelity-output.txt: Emit restart/reconcile signals when cone matches after reinstall even if VERIFIED_TARGET is false.
  - From dyn-release-step7-output.txt: After any uninstall/marketplace refresh/install path, emit `LARCH_RESTART_REQUIRED=true` whenever the install was mutated but stable verification failed (or have Step 7 treat non-zero `upgrade_rc` after a captured reinstall as `RESTART_REQUIRED=true` unless output explicitly says “No upgrade needed”).

### FINDING_10: Post-reinstall cone still mismatched exits 0 without restart signals
- **Reviewer(s)**: dyn-release-step7-output.txt
- **Severity**: important
- **Concern**: If `MARKETPLACE_CONE_WILL_RECONCILE=true` but `marketplace_sparse_cone_matches` is still false after reinstall while `VERIFIED_TARGET=true`, the script exits 0 with only a prose warning—no `LARCH_CONE_RECONCILED=true` or `LARCH_RESTART_REQUIRED=true`. Release Step 7 leaves restart flags false and Step 8 omits the restart instruction despite documented stale in-memory state after cone repair.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-release-step7-output.txt: On that branch, exit non-zero and/or always emit `LARCH_RESTART_REQUIRED=true`; optionally set `LARCH_CONE_RECONCILED=false` explicitly so release automation can warn that allowlist propagation did not complete.

### FINDING_11: Metadata cache-missing branch fails closed without fallthrough
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-release-step7-output.txt
- **Severity**: important
- **Concern**: When `get_installed_larch_version` returns a version but the matching cache directory is missing, `resolve_release_step7_root` returns failure immediately without trying `CURRENT_VERSION` or sole-cache fallbacks. Right after a release, metadata can name `NEW_VERSION` before that cache dir exists, so Step 7 skips the working-tree upgrade and falls through to the installed `/upgrade-larch` Skill—the pre-fix path that may still lack the new allowlist.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Fall through to CURRENT_VERSION and sole-cache fallbacks; add harness coverage
  - From dyn-release-step7-output.txt: If `metadata_root` is missing, fall through to prepare/sole-cache resolution (or run the working-tree script with `CLAUDE_PLUGIN_ROOT` unset so `SCRIPT_ROOT` still supplies the allowlist) instead of failing closed into the Skill fallback.

### FINDING_12: Release Step 7 prose vs env-file behavior on partial failure
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Release SKILL prose claims failed Step 7 does not persist state, but the Step 7 fence still writes an all-false `release-step7.env`. Operators may misread restart requirements after partial failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Align documentation with actual env-file behavior

### FINDING_13: Missing plan-required reconcile prose substring fallback
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Release Step 7 omits the plan-required reconcile prose substring fallback for `CONE_RECONCILED`. Same-version cone repair can print the reconcile banner without `LARCH_CONE_RECONCILED=true`, so Step 8 skips mandatory restart while marketplace state changed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Add substring fallback on successful capture or align acceptance/docs to machine-readable-only and ensure upgrade always emits the line when repair succeeds.

### FINDING_14: Stale active cache root — wrong diagnosis and no restart signal
- **Reviewer(s)**: dyn-bash-state-output.txt, dyn-harness-realism-output.txt
- **Severity**: important
- **Concern**: When metadata is already at `LATEST_STABLE` but the cache-shaped `PLUGIN_ROOT` basename lags (stale-active-root case), `already_latest_and_cone_ok` fails and the script sets `NEEDS_CONE_RECONCILE=true` with a misleading “sparse checkout is out of date” message without checking `MARKETPLACE_CONE_WILL_RECONCILE`. It reinstalls, emits neither `LARCH_CONE_RECONCILED=true` nor `LARCH_RESTART_REQUIRED=true`, and `/release` Step 7/8 finish without mandating restart despite stale in-memory plugin state. The `production-active-root-stale` test does not assert restart signals.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-state-output.txt: Gate `NEEDS_CONE_RECONCILE` and its operator message on `MARKETPLACE_CONE_WILL_RECONCILE=true` (or an equivalent explicit cone mismatch), and emit a separate stale-cache message plus `LARCH_RESTART_REQUIRED=true` when the cache-shaped `PLUGIN_ROOT` basename lags `LATEST_STABLE` while the cone already matches; extend `production-active-root-stale` to assert the correct machine-readable restart signal.
  - From dyn-harness-realism-output.txt: Add an explicit assertion: either `assert_failure` for `LARCH_RESTART_REQUIRED=true` (documenting that no restart signal is emitted and why this is intentional) or fix the production logic to compare `INSTALLED_VERSION` (from `PLUGIN_ROOT`) against `ACTUAL_VERSION` rather than `CURRENT_INSTALLED_VERSION` from metadata.

### FINDING_15: Skill-tool fallback described but not implemented in Step 7 fence
- **Reviewer(s)**: dyn-release-step7-output.txt, cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: When `RESOLVED_ROOT` is empty, the Step 7 `else` branch contains only prose comments describing Skill-tool `/upgrade-larch` invocation and output parsing. The following `release-step7.env` write always records all-false flags, so Step 8 never requests restart when the no-marketplace-root fallback is the only available path—even after a successful cone repair.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-release-step7-output.txt: Mirror the working-tree pattern in the fallback branch (capture `2>&1`, parse machine-readable lines, write `release-step7.env`) or state explicitly that fallback must not run without the same capture contract.
  - From cursor-specialist-security-output.txt: Implement the Skill-tool invocation in the `else` branch (or remove the promises made in the comment and document that the fallback path returns all-false state); do not leave executable code paths described only in prose.

### FINDING_16: SessionStart sparse probe does not mechanically isolate lib-sparse-dirs
- **Reviewer(s)**: dyn-hook-failopen-output.txt
- **Severity**: important
- **Concern**: The sparse-cone probe sources `lib-sparse-dirs.sh` in the parent shell before calling `append_msg` with a fixed literal. A tampered or buggy library (or future edit) could redefine `append_msg`, assign `MSG` at top level, or run code inside `normalize_sparse_dirs`, allowing attacker-controlled text into SessionStart context despite the call site appearing safe.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-hook-failopen-output.txt: Isolate allowlist loading (subshell or helper that prints the normalized list on stdout only), or snapshot/restore `append_msg`/`MSG` around a minimal source block; add a harness fixture lib that defines a hostile `append_msg` and assert the emitted `additionalContext` stays exactly the fixed sparse-drift string.

### FINDING_17: Sole-cache fallback does not verify current_version match
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `resolve_release_step7_root`'s last-resort `single_larch_cache_version_dir` fallback returns whatever sole directory exists without verifying it matches `current_version`. A release with `CURRENT_VERSION=47.0.72` but only cache dir `47.0.70` would bind `RESOLVED_ROOT` to the stale dir for prune/stamp, diverging from the plan's "sole defensible cache target" wording.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Gate the final fallback on `[ "$sole_root" = "$cache_parent/${current_version}" ]` (or at minimum only return it when `current_version` is non-empty), so a stale sole-cache-dir is not silently selected as the prune/stamp context for a different release.

### FINDING_18: shell_quote uses non-portable printf %q on Bash 3.2
- **Reviewer(s)**: dyn-sparse-install-output.txt
- **Severity**: latent
- **Concern**: The version-mismatch warning uses `shell_quote` with `printf '%q'`, which is unavailable in Bash 3.2 mandated by `BASH_AUTHORING.md`. On macOS Bash 3.2.57 the recovery line can render as `rm -rf ` with no path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-sparse-install-output.txt: Replace `shell_quote` with a portable single-quote escaping idiom: `sq() { printf "'%s'" "$(printf '%s' "$1" | sed "s/'/'\\''/g")"; }`, or simply emit the literal `~/.claude/plugins/marketplaces/larch-local` in the warning (acceptable because `marketplace_clone_path` always returns that fixed path).

### FINDING_19: LARCH_RESTART_REQUIRED=true emitted twice in one branch combination
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: When `MARKETPLACE_CONE_WILL_RECONCILE=true` and `LATEST_STABLE=""`, `LARCH_RESTART_REQUIRED=true` is emitted twice (cone-reconcile branch and unconditional `LATEST_STABLE=""` block). Harmless for substring-match callers today but obscures intent and could confuse future deduplicating consumers; no production test covers this combination.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: In the `LATEST_STABLE=""` block, guard with `if [ "$MARKETPLACE_CONE_WILL_RECONCILE" != true ]` or hoist `LARCH_RESTART_REQUIRED=true` to a single emission point.
  - From cursor-specialist-testing-output.txt: Guard the `[ -z "$LATEST_STABLE" ]` block at line 529 with `[ "$MARKETPLACE_CONE_WILL_RECONCILE" != true ]` (or an equivalent single-emission flag) so `LARCH_RESTART_REQUIRED=true` is emitted exactly once per run.

### FINDING_20: Dead export in production-unverified-reinstall test stub
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Inside the `production-unverified-reinstall` test's `claude` stub, `export LARCH_TEST_LIST_FAIL=true` in the `plugin install` handler cannot propagate to the parent process; the flag is already set via outer `env`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Remove the `export LARCH_TEST_LIST_FAIL=true` line from the stub's `plugin install` handler.

### FINDING_21: lib-sparse-dirs.md lists release-step7-root.sh as consumer incorrectly
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `lib-sparse-dirs.md` lists `release-step7-root.sh` as a consumer, but that file does not source `lib-sparse-dirs.sh` or use `LARCH_SPARSE_DIRS`/`normalize_sparse_dirs`, which may mislead future allowlist edits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Remove `skills/upgrade-larch/scripts/release-step7-root.sh` from the consumer list in `lib-sparse-dirs.md`.

### FINDING_22: RESOLVED_ROOT= parsing corrupts paths containing =
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `release-step7.env` writes `RESOLVED_ROOT=<path>` and Step 8 reads with `awk -F=`, truncating at embedded `=` characters in filesystem paths (e.g. `/Users/a=b/...`). Diagnostic corruption only—Step 8 does not use `RESOLVED_ROOT` for control flow.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Either strip `RESOLVED_ROOT` from the state file (it is not consumed in Step 8), or use a delimiter that cannot appear in a filesystem path (`|`, `\t`) or write/read it as the last field taking the rest of the line with `awk -F= 'NR==FNR && $1=="RESOLVED_ROOT"{print substr($0, index($0,"=")+1); exit}'`.

### FINDING_23: Harness inline source permanently overrides upgrade-larch function namespace
- **Reviewer(s)**: dyn-harness-realism-output.txt
- **Severity**: nit
- **Concern**: `resolve_release_step7_root_for_test` sources `release-step7-root.sh` inline, overriding helper definitions in the harness process. Test ordering is now load-bearing; a future case calling root resolution between unit tests and `source_upgrade_for_case` could silently use the wrong `is_cache_shaped_larch_root` implementation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-realism-output.txt: Run `resolve_release_step7_root` in a subprocess (`bash -c "source ...; resolve_release_step7_root ..."`) rather than sourcing into the harness namespace, or add an explicit `source_upgrade_for_case` guard after the root-resolution block to restore `upgrade-larch.sh` function definitions before proceeding.

### FINDING_24: No production test for LARCH_EXPECTED_STABLE_VERSION release path
- **Reviewer(s)**: dyn-harness-realism-output.txt
- **Severity**: nit
- **Concern**: `/release` Step 7 invokes `upgrade-larch.sh` with `LARCH_EXPECTED_STABLE_VERSION="$NEW_VERSION"`, but no production integration test sets this variable. A regression in the guard would go undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-realism-output.txt: Add a `production-release-expected-version` case that sets `LARCH_EXPECTED_STABLE_VERSION`, omits or fails the `gh` stub, and asserts that the correct `LATEST_STABLE` is used, `LARCH_NEW_VERSION_INSTALLED=true` is emitted (or `LARCH_CONE_RECONCILED=true` if cone-only), and the script exits 0.

### FINDING_25: test-sessionstart-health case 4f2 mislabeled
- **Reviewer(s)**: dyn-harness-realism-output.txt
- **Severity**: nit
- **Concern**: Case 4f2 is labeled as testing unset-variable failure under `set -u`, but `probe_sparse_cone_drift` does `set +u` before sourcing the stub library, so it exercises the same missing-`normalize_sparse_dirs` path as case 4f rather than the claimed `set -u` abort path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-realism-output.txt: Either rename case 4f2 to describe what it actually tests ("library defines no normalize_sparse_dirs via unrecognized syntax"), or restructure it to place `set -u` inside the library's function bodies and verify the `set +e` + `set +u` in `probe_sparse_cone_drift` still protects the hook.

### FINDING_26: cone-empty fixture construction is git-version fragile
- **Reviewer(s)**: dyn-harness-realism-output.txt
- **Severity**: nit
- **Concern**: The `cone-empty` case overwrites sparse-checkout internal state after `git sparse-checkout set --no-cone`; on git ≥ 2.36 with cone mode still configured, `git sparse-checkout list` may return stale patterns, producing a false pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-realism-output.txt: Construct the "empty sparse list" fixture without `sparse-checkout init`—use a bare `git init` without any `sparse-checkout` commands, then confirm `git sparse-checkout list` is empty, rather than overwriting internal state files.

### FINDING_27: gh stubs in production tests do not validate subcommand shape
- **Reviewer(s)**: dyn-harness-realism-output.txt
- **Severity**: nit
- **Concern**: All `gh` stubs match any arguments and print `v9.0.0`; a refactor from `gh api` to `gh release list` would still pass tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-realism-output.txt: Add a minimal argument check inside each `gh` stub: `case "$1 $2" in "api "*)` to verify the `api` subcommand is reached, and `exit 1` on mismatch, so a command-shape regression is caught.

### FINDING_28: probe_sparse_cone_drift duplicates shell-opt restore on each early return
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `probe_sparse_cone_drift` restores `set -e`/`set -u` with identical blocks before each of three early `return 0` paths. A future early-exit path that omits restore could leave errexit/nounset disabled for the rest of the hook.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Move the restore into a `trap ... RETURN` set at function entry, or extract a single helper function (`restore_shell_opts`) called by all exit paths.

### OOS_1: [OUT_OF_SCOPE] test-upgrade-larch-retention.sh harness could be split by concern
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Harness file grew to 693 lines; new cone cases add bulk but follow a consistent per-case HOME pattern. Splitting into `test-upgrade-larch-cone.sh` and `test-upgrade-larch-retention.sh` is a follow-up readability improvement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Consider splitting into test-upgrade-larch-cone.sh and test-upgrade-larch-retention.sh in a follow-up

### OOS_2: [OUT_OF_SCOPE] get_stable_releases uses first API stable tag not semver max
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Pre-existing: `get_stable_releases` picks the first stable tag from the GitHub API rather than semver-max, which can mis-resolve `LATEST_STABLE` if release list order is not newest-first.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Use semver comparison to select latest stable tag

### OOS_3: [OUT_OF_SCOPE] get_installed_larch_version HOME guard alignment when refactoring
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt, dyn-bash-state-output.txt
- **Severity**: latent
- **Concern**: Pre-existing divergence: `upgrade-larch.sh`'s `get_installed_larch_version` dereferences `$HOME/.claude/plugins/installed_plugins.json` without an empty-`HOME` guard; the new `release-step7-root.sh` path is safer. Worth aligning when touching install metadata reads.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Consolidate into one sourced helper when refactoring root resolution.
  - From dyn-bash-state-output.txt: (no separate fix beyond consolidation note in concern)

### OOS_4: [OUT_OF_SCOPE] Reconcile prose substring fallback intentionally omitted
- **Reviewer(s)**: dyn-bash-state-output.txt
- **Severity**: latent
- **Concern**: The plan called for a fixed reconcile prose fragment fallback when machine lines are absent; implementation and harness intentionally accept only `LARCH_CONE_RECONCILED=true`. Deliberate tightening increases reliance on machine-line emission being correct (see FINDING_14).
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_5: [OUT_OF_SCOPE] release-step7.env lives in ephemeral prepare temp dir
- **Reviewer(s)**: dyn-release-step7-output.txt
- **Severity**: latent
- **Concern**: Pre-existing pattern now more visible: `release-step7.env` lives under Step 2's `mktemp` prepare dir with no durable recovery copy (unlike release notes). Step 6-only recovery re-runs cannot read cone/restart flags from a prior partial release.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_6: [OUT_OF_SCOPE] Pre-existing SessionStart advisories interpolate local file contents
- **Reviewer(s)**: dyn-hook-failopen-output.txt
- **Severity**: latent
- **Concern**: Pre-existing SessionStart advisories (e.g. `larch-stalled-run.txt`) interpolate local file contents into `MSG` and then into `jq --arg`; larger prompt-injection surface outside this branch's sparse probe.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_7: [OUT_OF_SCOPE] Sparse probe gated on jq and git availability
- **Reviewer(s)**: dyn-hook-failopen-output.txt
- **Severity**: nit
- **Concern**: Environments missing `jq` never get the sparse drift warning (availability limitation, not a fail-open violation).
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_8: [OUT_OF_SCOPE] probe_sparse_cone_drift shell-opt restore pattern fragile on future edits
- **Reviewer(s)**: dyn-sparse-install-output.txt
- **Severity**: nit
- **Concern**: `case $-` save/restore in `probe_sparse_cone_drift` is fine as written but fragile if future `set -e`-sensitive additions exit before restoration lines; cleaner idiom would be subshell isolation or bash 4.4+ `local -`.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_9: [OUT_OF_SCOPE] Misleading cone-drift message on stale-active-root predates this diff
- **Reviewer(s)**: dyn-harness-realism-output.txt
- **Severity**: latent
- **Concern**: When `CURRENT_INSTALLED_VERSION == LATEST_STABLE` but only `PLUGIN_ROOT` basename is stale, the "sparse checkout is out of date" message is semantically wrong. Pre-existing before this diff; new code path makes it more reachable (see FINDING_14 for in-scope fix).
- **Suggested revisions (informational for voters; coder decides)**:
