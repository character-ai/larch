### FINDING_1: Release Step 7 cache-root resolution is prose-only and can target the wrong plugin root
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-sparse-rooting-output.txt, dyn-release-flow-output.txt
- **Severity**: important
- **Concern**: Step 7’s `RESOLVED_ROOT` ordering and cache-shape validation live in prose / mirrored test helper logic rather than a production helper invoked by the runnable Bash fence. An orchestrator can leave `RESOLVED_ROOT` empty or choose a non-cache/stale root, causing fallback to the cached `/upgrade-larch` skill path or unsafe prune/reconcile behavior against the wrong directory.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-sparse-rooting-output.txt, dyn-release-flow-output.txt: Address the concern above.


### FINDING_14: `LARCH_NEW_VERSION_INSTALLED=true` can be emitted for unverified installs when `gh` cannot resolve latest stable
- **Reviewer(s)**: dyn-cli-signals-output.txt
- **Severity**: important
- **Concern**: If `LATEST_STABLE` is empty because `gh` fails, the script can still emit `LARCH_NEW_VERSION_INSTALLED=true` based on version difference while verification remains false and the script exits 0. `/release` may then require a restart after a best-effort, unverified install.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cli-signals-output.txt: Address the concern above.


### FINDING_15: Failed post-install version resolution can suppress required restart state
- **Reviewer(s)**: dyn-cli-signals-output.txt
- **Severity**: important
- **Concern**: If `get_installed_larch_version` fails after install, `LARCH_NEW_VERSION_INSTALLED=true` may not be emitted and the script may still exit 0 when `LATEST_STABLE` is empty. Step 8 can skip restart guidance even though the plugin may have changed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cli-signals-output.txt: Address the concern above.


### FINDING_2: `LARCH_CONE_RECONCILED=true` is emitted before verified successful cone repair
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-sparse-rooting-output.txt, dyn-cli-signals-output.txt, dyn-release-flow-output.txt, dyn-sparse-git-output.txt
- **Severity**: important
- **Concern**: `upgrade-larch.sh` emits `LARCH_CONE_RECONCILED=true` from a pre-run drift flag instead of after successful reinstall, stable-version verification, same-version reconcile gating, and/or a post-install sparse-cone match. Failed or partial upgrades can therefore advertise a successful cone repair and mislead `/release` Step 8 and operators.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-sparse-rooting-output.txt, dyn-cli-signals-output.txt, dyn-release-flow-output.txt, dyn-sparse-git-output.txt: Address the concern above.


### FINDING_5: Missing sparse-dir library fails with a generic shell source error
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `upgrade-larch.sh` sources `lib-sparse-dirs.sh` without an explicit missing-file check, making wrong `SCRIPT_ROOT` or incomplete checkout failures harder for operators to diagnose during `/release` Step 7.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_6: Release Step 7 honors machine flags even when `upgrade-larch` exits nonzero
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-sparse-rooting-output.txt, dyn-cli-signals-output.txt, dyn-release-flow-output.txt, dyn-sparse-git-output.txt
- **Severity**: important
- **Concern**: Step 7 sets and persists `CONE_RECONCILED` / `NEW_VERSION_INSTALLED` from captured output without requiring `upgrade_rc=0`. A failed upgrade can therefore write success-looking state into `release-step7.env`, and Step 8 can require a restart even though the install or cone repair failed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-sparse-rooting-output.txt, dyn-cli-signals-output.txt, dyn-release-flow-output.txt, dyn-sparse-git-output.txt: Address the concern above.


### FINDING_8: Already-latest matching-cone production early exit lacks full-script coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The test suite lacks a hermetic full-script case for the already-latest + matching-cone early exit, so regressions could reinstall every run or skip stamp/prune behavior while unit helper tests still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


