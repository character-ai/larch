### FINDING_1: Release Step 7 root resolution is prompt-only instead of a shared executable resolver
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-release-state-output.txt, dyn-sparse-contract-output.txt
- **Severity**: important
- **Concern**: Release Step 7’s `RESOLVED_ROOT` ordering is described in prose or mirrored only in tests, so `/release` can pick a different plugin root than the harness and run upgrade/prune/stamp logic against the wrong cache.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-release-state-output.txt, dyn-sparse-contract-output.txt: Address the concern above.

### FINDING_2: Cone-reconcile coverage does not exercise real `upgrade-larch.sh` on a drifted marketplace
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-harness-isolation-output.txt
- **Severity**: important
- **Concern**: Tests rely on helper/stub/string-fragment checks instead of a hermetic run of production `upgrade-larch.sh` against a drifted sparse checkout, so regressions in early-exit bypass, reconcile wiring, or `LARCH_CONE_RECONCILED=true` emission can pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-harness-isolation-output.txt: Address the concern above.

### FINDING_3: Sparse-cone comparison logic is duplicated outside `lib-sparse-dirs.sh`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-sparse-contract-output.txt
- **Severity**: nit
- **Concern**: SessionStart and upgrade-larch each implement sparse-cone comparison rules separately, so future rule changes can make warn-only and reconcile paths disagree.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, dyn-sparse-contract-output.txt: Address the concern above.

### FINDING_4: SessionStart tests duplicate the sparse allowlist literal
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, dyn-harness-isolation-output.txt, dyn-sparse-contract-output.txt
- **Severity**: latent
- **Concern**: `scripts/test-sessionstart-health.sh` hardcodes the expected sparse dirs instead of deriving from `lib-sparse-dirs.sh`, allowing allowlist edits to desync SessionStart coverage from production.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, dyn-harness-isolation-output.txt, dyn-sparse-contract-output.txt: Address the concern above.

### FINDING_5: Root-resolution tests miss metadata-vs-`CURRENT_VERSION` mismatch cases
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-release-state-output.txt, dyn-harness-isolation-output.txt
- **Severity**: important
- **Concern**: The harness does not pin cases where installed metadata and prepare `CURRENT_VERSION` disagree while multiple cache directories exist, so release root selection can silently fall back to the wrong cache path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-release-state-output.txt, dyn-harness-isolation-output.txt: Address the concern above.

### FINDING_6: Repeatedly sourcing `upgrade-larch.sh` can leak ERR traps into the harness
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Sourcing `upgrade-larch.sh` repeatedly in the parent harness can re-register recovery traps, so unrelated harness errors may invoke production recovery behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] Security prune-trust docs still describe the old idempotent path
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `SECURITY.md` still says prune skips on already-latest idempotence without qualifying that same-version cone reconcile can now run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] Docs and skill prose duplicate illustrative sparse literals
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-sparse-contract-output.txt
- **Severity**: nit
- **Concern**: Installation docs, skills docs, and upgrade skill prose still include manual sparse-dir literals that can drift from `lib-sparse-dirs.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, dyn-sparse-contract-output.txt: Address the concern above.

### FINDING_9: `NEW_VERSION_INSTALLED` detection is tied to brittle pre-success output
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-upgrade-flow-output.txt, dyn-release-state-output.txt
- **Severity**: important
- **Concern**: Release Step 7 infers `NEW_VERSION_INSTALLED` from upgrade banner text instead of successful verification or a machine signal, causing both missed restarts and false-positive restarts depending on output shape and failure timing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, dyn-upgrade-flow-output.txt, dyn-release-state-output.txt: Address the concern above.

### FINDING_10: `CONE_RECONCILED` can be set from a pre-install banner before upgrade success
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-upgrade-flow-output.txt, dyn-release-state-output.txt
- **Severity**: important
- **Concern**: Release Step 7 treats the reconcile intent fragment as success even though `upgrade-larch.sh` prints it before uninstall/reinstall/verification, so a failed repair can still trigger Step 8 restart guidance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-upgrade-flow-output.txt, dyn-release-state-output.txt: Address the concern above.

### FINDING_11: Missing retention coverage for empty configured sparse-checkout lists
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: There is no case for an empty sparse-checkout configuration, so hook silence and upgrade reconcile behavior can diverge without CI signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] Release Step 7 harness coverage is still missing
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-upgrade-flow-output.txt, dyn-harness-isolation-output.txt
- **Severity**: latent
- **Concern**: Release Step 7 root/state parsing remains a prompt-orchestrator contract without a dedicated `test-release-*` executable harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, dyn-upgrade-flow-output.txt, dyn-harness-isolation-output.txt: Address the concern above.

### FINDING_13: Cone reconcile can uninstall before reinstall success is guaranteed
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Same-version cone repair uninstalls before successful reinstall/verification, so a mid-path failure can leave larch uninstalled and the cone still drifted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_14: SessionStart drift probe silently skips installs missing `lib-sparse-dirs.sh`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Users on pre-fix/corrupted installs lacking `lib-sparse-dirs.sh` get no sparse-drift advisory until a successful upgrade/restart delivers the library.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_15: Missing explicit operator error when `lib-sparse-dirs.sh` cannot be sourced
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: A missing/corrupted sparse dirs library currently fails with a generic Bash source error rather than an actionable larch error naming the script root.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] Cone matching ignores `known_marketplaces.json` `sparsePaths`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: JSON-only `sparsePaths` drift can be missed when the git sparse cone itself matches.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] `get_installed_larch_version` lacks an empty-`HOME` guard
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Empty `HOME` can make installed metadata reads fail unpredictably.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_18: `LARCH_CONE_RECONCILED=true` is gated too tightly on stable-version verification
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt, dyn-harness-isolation-output.txt, dyn-sparse-contract-output.txt
- **Severity**: latent
- **Concern**: Successful same-version cone repair may not emit the machine restart signal when later version verification fails or `LATEST_STABLE` is unavailable, leaving release parsing to fragile substring inference or causing missed restarts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt, dyn-harness-isolation-output.txt, dyn-sparse-contract-output.txt: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] Standalone `/upgrade-larch` still uses the installed script path during bootstrap
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Pre-fix installs may need a release/version bump before standalone `/upgrade-larch` picks up the fixed script.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_20: Already-latest early exit ignores the active cache version
- **Reviewer(s)**: dyn-upgrade-flow-output.txt
- **Severity**: important
- **Concern**: `already_latest_and_cone_ok()` checks installed metadata against latest stable but not the running `CLAUDE_PLUGIN_ROOT` version, so after an upgrade without restart it can early-exit while the active cache remains stale.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-upgrade-flow-output.txt: Address the concern above.

### FINDING_21: SessionStart sparse-drift probe is unnecessarily gated on `jq`
- **Reviewer(s)**: dyn-upgrade-flow-output.txt
- **Severity**: latent
- **Concern**: Environments with `git` but without `jq` skip sparse-drift warnings even though the probe can run without jq.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-upgrade-flow-output.txt: Address the concern above.

### FINDING_22: [OUT_OF_SCOPE] Latest stable tag selection is not semver-sorted
- **Reviewer(s)**: dyn-upgrade-flow-output.txt
- **Severity**: latent
- **Concern**: `LATEST_STABLE` uses the first valid tag returned by `gh api`, which can misclassify upgrade state if tags are not sorted as expected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-upgrade-flow-output.txt: Address the concern above.

### FINDING_23: Skill-tool fallback can reconcile without updating `release-step7.env`
- **Reviewer(s)**: dyn-release-state-output.txt
- **Severity**: important
- **Concern**: When `RESOLVED_ROOT` is empty, Step 7 writes false state before the prose fallback; if the fallback repairs the cone, Step 8 may skip the required restart because no captured output rewrites the env file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-release-state-output.txt: Address the concern above.

### FINDING_24: [OUT_OF_SCOPE] Step 8 restart state depends on fragile tempdir re-derivation
- **Reviewer(s)**: dyn-release-state-output.txt
- **Severity**: latent
- **Concern**: If the orchestrator loses the Step 2 temp artifact path, missing `release-step7.env` defaults both restart flags false and can silently skip restart guidance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-release-state-output.txt: Address the concern above.

### FINDING_25: [OUT_OF_SCOPE] Upgrade script signal semantics still need tightening after verification failure
- **Reviewer(s)**: dyn-release-state-output.txt
- **Severity**: latent
- **Concern**: Same-version cone repair does not emit `LARCH_CONE_RECONCILED=true` when verification fails, even though the preamble was printed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-release-state-output.txt: Address the concern above.

### FINDING_26: SessionStart harness does not actually prove independence from later `PLUGIN_ROOT`
- **Reviewer(s)**: dyn-harness-isolation-output.txt
- **Severity**: latent
- **Concern**: The labeled test only proves `HOOK_CWD` independence and never reaches the later `PLUGIN_ROOT` path, so the intended acceptance criterion remains untested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-isolation-output.txt: Address the concern above.

### FINDING_27: [OUT_OF_SCOPE] Committed run-log files add unrelated diff noise
- **Reviewer(s)**: dyn-harness-isolation-output.txt
- **Severity**: nit
- **Concern**: The branch includes committed `larch-logs/implement/...` run-log content unrelated to the harness changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-isolation-output.txt: Address the concern above.

### FINDING_28: [OUT_OF_SCOPE] `NEW_VERSION_INSTALLED` glob remains brittle
- **Reviewer(s)**: dyn-harness-isolation-output.txt
- **Severity**: nit
- **Concern**: The release Step 7 glob for new-version detection is fragile compared with explicit substring or machine-signal parsing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-isolation-output.txt: Address the concern above.

### FINDING_29: [OUT_OF_SCOPE] Existing v47.0.70 sparse-cone symptom is operational debt
- **Reviewer(s)**: dyn-sparse-contract-output.txt
- **Severity**: latent
- **Concern**: The missing-`python/` marketplace cone symptom is pre-existing operational debt rather than a regression introduced by this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-sparse-contract-output.txt: Address the concern above.

### FINDING_30: Recovery command display breaks when `$HOME` contains a single quote
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `$marketplace_clone` is shown inside single quotes in an advisory `rm -rf` command; a literal quote in `HOME` produces a broken copy-paste command.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
