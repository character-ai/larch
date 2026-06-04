### FINDING_1: Release Step 7 cache-root resolution is prose-only and can target the wrong plugin root
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-sparse-rooting-output.txt, dyn-release-flow-output.txt
- **Severity**: important
- **Concern**: Step 7’s `RESOLVED_ROOT` ordering and cache-shape validation live in prose / mirrored test helper logic rather than a production helper invoked by the runnable Bash fence. An orchestrator can leave `RESOLVED_ROOT` empty or choose a non-cache/stale root, causing fallback to the cached `/upgrade-larch` skill path or unsafe prune/reconcile behavior against the wrong directory.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-sparse-rooting-output.txt, dyn-release-flow-output.txt: Address the concern above.

### FINDING_2: `LARCH_CONE_RECONCILED=true` is emitted before verified successful cone repair
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-sparse-rooting-output.txt, dyn-cli-signals-output.txt, dyn-release-flow-output.txt, dyn-sparse-git-output.txt
- **Severity**: important
- **Concern**: `upgrade-larch.sh` emits `LARCH_CONE_RECONCILED=true` from a pre-run drift flag instead of after successful reinstall, stable-version verification, same-version reconcile gating, and/or a post-install sparse-cone match. Failed or partial upgrades can therefore advertise a successful cone repair and mislead `/release` Step 8 and operators.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-sparse-rooting-output.txt, dyn-cli-signals-output.txt, dyn-release-flow-output.txt, dyn-sparse-git-output.txt: Address the concern above.

### FINDING_3: Release Step 7 dropped the planned reconcile-prose fallback
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-sparse-rooting-output.txt
- **Severity**: important
- **Concern**: Step 7 parses only machine-readable `LARCH_CONE_RECONCILED=true` / `LARCH_NEW_VERSION_INSTALLED=true` lines, while the plan expected a fallback based on same-version reconcile prose. Older, partial, or buggy output could repair the cone without the machine line, causing Step 8 to skip a required restart; tests and docs also contradict the planned fallback.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-sparse-rooting-output.txt: Address the concern above.

### FINDING_4: Sparse-cone comparison logic is duplicated and handles empty/error cases inconsistently
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, dyn-sparse-git-output.txt
- **Severity**: latent
- **Concern**: `sessionstart-health.sh` and `upgrade-larch.sh` duplicate sparse-cone comparison logic and diverge on empty or failed `git sparse-checkout list` output. Future normalization changes can drift, and operators may get no SessionStart hint while `/upgrade-larch` repeatedly takes a heavy reinstall path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, dyn-sparse-git-output.txt: Address the concern above.

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

### FINDING_7: Already-latest early exit can ignore stale or incomplete active cache contents
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-sparse-rooting-output.txt
- **Severity**: latent
- **Concern**: The early-exit path trusts metadata/latest-version and sparse-cone equality without proving the active `PLUGIN_ROOT` cache actually contains allowlisted directories or matches the metadata version. A stale or partially populated cache can skip reinstall and continue missing newly allowlisted runtime directories.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-sparse-rooting-output.txt: Address the concern above.

### FINDING_8: Already-latest matching-cone production early exit lacks full-script coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The test suite lacks a hermetic full-script case for the already-latest + matching-cone early exit, so regressions could reinstall every run or skip stamp/prune behavior while unit helper tests still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_9: Same-version drift reconcile E2E coverage is incomplete
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The production-drift test stub does not exercise the intended same-version reconcile path or assert absence of a from-X-to-X upgrade banner. RC2 regressions could pass tests through an unconditional upgrade path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_10: Release Step 7/8 env-state and restart gating lack offline harness coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The Step 7 state-file write/read and Step 8 restart-gating behavior are prompt-only, so typos or parsing mistakes could leave operators without required restart guidance after cone repair.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] Cached `/upgrade-larch` entrypoint cannot bootstrap fixes from a pre-fix cache
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-sparse-rooting-output.txt
- **Severity**: latent
- **Concern**: The `/upgrade-larch` skill runs the cached script under `CLAUDE_PLUGIN_ROOT`, so broken pre-fix caches may continue running old logic until a release working-tree invocation or version bump installs the new script and library.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, dyn-sparse-rooting-output.txt: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] Installed-version metadata can disagree with `PLUGIN_ROOT` basename
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `get_installed_larch_version` can disagree with the active cache-root basename, creating ambiguity between metadata-driven idempotency and `PLUGIN_ROOT`-based prune behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_13: Sparse-dir library documentation omits ShellCheck / agent-lint contract
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `scripts/lib-sparse-dirs.md` lacks the planned note explaining ShellCheck line-1 and `agent-lint.toml` exclusion rationale, making future edits easier to mis-handle.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

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

### FINDING_16: [OUT_OF_SCOPE] Negative tests for failed reconcile signaling are absent
- **Reviewer(s)**: dyn-cli-signals-output.txt
- **Severity**: nit
- **Concern**: There is no harness case proving that failed verification with `upgrade_rc=1` cannot set `CONE_RECONCILED` through captured output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cli-signals-output.txt: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] Release-tag propagation race can choose previous stable
- **Reviewer(s)**: dyn-release-flow-output.txt
- **Severity**: latent
- **Concern**: If GitHub releases do not surface the just-cut tag immediately after promotion, Step 7 may reconcile against the previous stable version rather than installing `NEW_VERSION`; this timing hazard predates the sparse-allowlist work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-release-flow-output.txt: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] Intentional sparse-dir word splitting is pre-existing
- **Reviewer(s)**: dyn-sparse-git-output.txt
- **Severity**: nit
- **Concern**: The unquoted `--sparse $LARCH_SPARSE_DIRS` word splitting is intentionally shellcheck-suppressed for space-separated top-level tokens and is not a regression from this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-sparse-git-output.txt: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] `gh`-unavailable unconditional reinstall behavior is longstanding
- **Reviewer(s)**: dyn-sparse-git-output.txt
- **Severity**: nit
- **Concern**: When `gh` cannot resolve `LATEST_STABLE`, `already_latest_and_cone_ok` cannot early-exit and may reinstall without the reconcile banner; this is documented longstanding behavior, not introduced here.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-sparse-git-output.txt: Address the concern above.

### FINDING_20: [OUT_OF_SCOPE] Run-log churn is unrelated to sparse-cone logic
- **Reviewer(s)**: dyn-sparse-git-output.txt
- **Severity**: nit
- **Concern**: Commit `53bb3d6d6` only changes `larch-logs/` implement run-log files and is unrelated to the sparse-cone review surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-sparse-git-output.txt: Address the concern above.
