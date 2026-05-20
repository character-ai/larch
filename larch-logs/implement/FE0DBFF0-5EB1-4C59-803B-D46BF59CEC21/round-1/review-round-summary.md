# Review Round 1

- Mode: `diff`
- Accepted findings: 20
- Rejected findings: 9
- Exonerated findings: 4
- Neutral findings: 1

## Accepted Findings

### FINDING_1: **correctness** `scripts/check-stale-plugin.sh:77-83` — `extract_version` runs `grep '"version"' "$1"` under `set -euo pipefail`, so a missing `"version"` field, an unreadable file, or any `grep` non-match aborts the whole script with exit status 1, which contradicts the header contract that normal output “always exits 0” (lines 18–25) and means the comparison/skip branches after lines 85–88 are never reached in those cases. **Suggested fix:** Make version extraction failure non-fatal inside the function (for example tolerate `grep` failure with `|| true`, or use `if grep …; then …; else printf ''; fi`), then treat an empty extracted version as `STALE_PLUGIN_CHECK=skip` so the helper truly always exits 0 for benign or malformed `plugin.json` inputs.
- **Reviewer**: dyn-session-wiring-output.txt
- **Concern**: - **correctness** `scripts/check-stale-plugin.sh:77-83` — `extract_version` runs `grep '"version"' "$1"` under `set -euo pipefail`, so a missing `"version"` field, an unreadable file, or any `grep` non-match aborts the whole script with exit status 1, which contradicts the header contract that normal output “always exits 0” (lines 18–25) and means the comparison/skip branches after lines 85–88 are never reached in those cases. **Suggested fix:** Make version extraction failure non-fatal inside the function (for example tolerate `grep` failure with `|| true`, or use `if grep …; then …; else printf ''; fi`), then treat an empty extracted version as `STALE_PLUGIN_CHECK=skip` so the helper truly always exits 0 for benign or malformed `plugin.json` inputs.
- **Suggested revision**: Address the concern above.


### FINDING_12: architecture: scripts/check-stale-plugin.sh:18-36
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Doc says always exit 0 unknown option exits 1 Direct invokers or tests see exit 1 vs documented warn-only exit 0 Document diagnostic exit or make unknown options soft-fail at exit 0
- **Suggested revision**: Address the concern above.


### FINDING_15: code-quality: docs/installation-and-setup.md:75
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Overclaims once per session and any larch skill Misleading expectations for skills that skip session-setup or for multiple setup calls in one Claude session Rephrase to per session-setup and name representative skills
- **Suggested revision**: Address the concern above.


### FINDING_16: code-quality: docs/linting.md (missing)
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] New harness not listed beside peers like test-check-clean-tree Contributors relying on docs/linting.md may not discover make test-check-stale-plugin Add a table row mirroring other script harness entries
- **Suggested revision**: Address the concern above.


### FINDING_18: code-quality: scripts/check-stale-plugin.md:1-3
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Contract claims always exit 0 but script exits 1 on unknown CLI Operators reading the contract may assume argv mistakes are also warn-only Qualify exit 0 to detection-only outcomes; document exit 1 for argv errors
- **Suggested revision**: Address the concern above.


### FINDING_19: code-quality: scripts/check-stale-plugin.sh:328-336
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Header claims always exit 0 but unknown flags exit 1 Typo flags yield exit 1 despite warn-only framing in comments Clarify comment or map bad-args to skip with exit 0
- **Suggested revision**: Address the concern above.


### FINDING_2: **correctness** `scripts/check-stale-plugin.sh:77-88` — With `set -euo pipefail`, `extract_version` runs `grep '"version"' "$1" | head -1 | sed …`; if `grep` finds no match it exits 1 and, under `pipefail`, the pipeline’s non-zero status can abort the whole script before the intended `[ -z "$INSTALLED_VERSION" ] || [ -z "$WT_VERSION" ]` branch runs, so the advertised “always exits 0” behavior and graceful `skip` handling for missing/parseable version fields are not guaranteed. **Suggested fix:** Stop the pipeline from failing on “no match” (for example append `|| true` to `grep`, use `grep … || :` before `sed`, or temporarily `set +e` around the extraction) so empty `INSTALLED_VERSION`/`WT_VERSION` reliably falls through to the existing `skip` logic.
- **Reviewer**: dyn-bash32-portability-output.txt
- **Concern**: - **correctness** `scripts/check-stale-plugin.sh:77-88` — With `set -euo pipefail`, `extract_version` runs `grep '"version"' "$1" | head -1 | sed …`; if `grep` finds no match it exits 1 and, under `pipefail`, the pipeline’s non-zero status can abort the whole script before the intended `[ -z "$INSTALLED_VERSION" ] || [ -z "$WT_VERSION" ]` branch runs, so the advertised “always exits 0” behavior and graceful `skip` handling for missing/parseable version fields are not guaranteed. **Suggested fix:** Stop the pipeline from failing on “no match” (for example append `|| true` to `grep`, use `grep … || :` before `sed`, or temporarily `set +e` around the extraction) so empty `INSTALLED_VERSION`/`WT_VERSION` reliably falls through to the existing `skip` logic.
- **Suggested revision**: Address the concern above.


### FINDING_20: correctness: docs/installation-and-setup.md:75
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Doc claims warning fires once per session Operators may expect a single warning per Claude session but see repeats whenever session-setup runs again Reword to per session-setup invocation or define session precisely
- **Suggested revision**: Address the concern above.


### FINDING_22: correctness: scripts/check-stale-plugin.sh:27-88
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] pipefail + grep pipeline can exit non-zero before empty-version skip Malformed or version-less plugin.json causes check-stale-plugin.sh to exit 1; contradicts always-exit-0 and skip contract; session-setup hides it Make grep/sed extraction tolerant (no failing grep under pipefail); then use empty-token skip as intended
- **Suggested revision**: Address the concern above.


### FINDING_23: correctness: scripts/check-stale-plugin.sh:32-37
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] CLI flags lack value presence guards Truncated argv can error under set -u Add [[ $# -ge 2 ]] checks before shift 2
- **Suggested revision**: Address the concern above.


### FINDING_24: correctness: scripts/check-stale-plugin.sh:328-335,346
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Contract says always exit 0; unknown options exit 1 Callers or docs treating exit code as always zero could mis-handle CLI misuse Document exit 1 for invalid args or relax parser to stay warn-only zero
- **Suggested revision**: Address the concern above.


### FINDING_25: correctness: scripts/check-stale-plugin.sh:37,78-83
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] set -euo pipefail + extract_version grep pipeline exits non-zero when plugin.json lacks a version line instead of emitting STALE_PLUGIN_CHECK=skip Corrupt or incomplete plugin.json without "version" aborts the helper; session-setup swallows the failure so skew is never reported and diagnostics are lost Make grep/pipeline fail-soft so empty versions reach the existing skip branch; add a harness fixture for missing version
- **Suggested revision**: Address the concern above.


### FINDING_28: correctness: scripts/check-stale-plugin.sh:77-88
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] extract_version uses grep in a pipefail pipeline When plugin.json has no matching "version" line grep exits 1 the whole script aborts non-zero session-setup masks with || true so skew is silent and contract says exit 0 Make grep non-fatal treat empty version as skip add harness align exit contract
- **Suggested revision**: Address the concern above.


### FINDING_3: **risk-integration** `scripts/session-setup.sh:207-212` — The stale check is invoked as `_stale_out=$("$SCRIPT_DIR/check-stale-plugin.sh" 2>/dev/null || true)`, which intentionally prevents `session-setup.sh` from failing when the helper exits non-zero and also discards the helper’s stderr; combined with the `grep`/`set -e` hazard above, a skew warning can be dropped with no operator-visible diagnostic, and even after hardening the helper this wrapper still hides genuine stderr-only failures (for example unexpected aborts) unless you add an explicit `larch_err`/breadcrumb path. **Suggested fix:** First harden `check-stale-plugin.sh` so non-zero exits are unexpected, then either remove `2>/dev/null` for the happy path or map `rc!=0` to a single `larch_err` line (still exiting 0 from `session-setup.sh`) so “warn-only” does not mean “silent.”
- **Reviewer**: dyn-session-wiring-output.txt
- **Concern**: - **risk-integration** `scripts/session-setup.sh:207-212` — The stale check is invoked as `_stale_out=$("$SCRIPT_DIR/check-stale-plugin.sh" 2>/dev/null || true)`, which intentionally prevents `session-setup.sh` from failing when the helper exits non-zero and also discards the helper’s stderr; combined with the `grep`/`set -e` hazard above, a skew warning can be dropped with no operator-visible diagnostic, and even after hardening the helper this wrapper still hides genuine stderr-only failures (for example unexpected aborts) unless you add an explicit `larch_err`/breadcrumb path. **Suggested fix:** First harden `check-stale-plugin.sh` so non-zero exits are unexpected, then either remove `2>/dev/null` for the happy path or map `rc!=0` to a single `larch_err` line (still exiting 0 from `session-setup.sh`) so “warn-only” does not mean “silent.”
- **Suggested revision**: Address the concern above.


### FINDING_31: correctness: scripts/session-setup.sh:207
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] stderr from check-stale-plugin.sh is discarded entirely Real failures can hide completely and the version-skew warning never appears with no explanation Stop redirecting stderr to /dev/null or only suppress known-safe noise
- **Suggested revision**: Address the concern above.


### FINDING_35: risk-integration: scripts/session-setup.sh:206-213
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] check-stale-plugin wrapped in 2>/dev/null || true masks all failures and stderr from the helper Any non-zero exit or stderr from the checker (including pipefail from grep) is silently ignored while session setup continues Remove || true once helper is fail-soft on all detection paths; or on non-zero status emit a single larch_err instead of full silence
- **Suggested revision**: Address the concern above.


### FINDING_36: risk-integration: scripts/session-setup.sh:206-213
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] 2>/dev/null and || true swallow all helper failures Any non-zero exit from check-stale-plugin yields no warning and no diagnostic; skew check can fail silently Remove blanket masking after helper is hardened; optionally larch_err on unexpected rc
- **Suggested revision**: Address the concern above.


### FINDING_39: risk-integration: scripts/test-check-stale-plugin.sh:1-126
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Plan testing strategy listed missing CLAUDE_PLUGIN_ROOT (and broadly missing plugin.json) but harness omits unset-env default path and WT plugin.json missing case Regression gap: default-env skip path and WT-missing skip are untested despite being named in the plan Add harness subprocess cases or trim the plan’s promised edge matrix
- **Suggested revision**: Address the concern above.


### FINDING_4: **risk-integration** `scripts/session-setup.sh:212` — The warning points dev-clone users at `/larch:upgrade-larch`, but `skills/upgrade-larch/scripts/upgrade-larch.sh:234-238` re-adds the GitHub marketplace and installs the latest stable release, not the current working tree; `docs/skills.md:201` also says local-checkout users should not use that flow. Concrete scenario: a local clone has unreleased working-tree version `29.8.40` and the cache has stable `29.8.39`; the warning fires, `/larch:upgrade-larch` reinstalls or no-ops at GitHub stable `29.8.39`, and the next run is still stale. **Suggested fix:** Change the warning and new docs to tell local-marketplace users to reinstall/refresh from the current checkout, or teach `/upgrade-larch` an explicit local-checkout refresh mode and only recommend it when it actually installs the working-tree version.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: - **risk-integration** `scripts/session-setup.sh:212` — The warning points dev-clone users at `/larch:upgrade-larch`, but `skills/upgrade-larch/scripts/upgrade-larch.sh:234-238` re-adds the GitHub marketplace and installs the latest stable release, not the current working tree; `docs/skills.md:201` also says local-checkout users should not use that flow. Concrete scenario: a local clone has unreleased working-tree version `29.8.40` and the cache has stable `29.8.39`; the warning fires, `/larch:upgrade-larch` reinstalls or no-ops at GitHub stable `29.8.39`, and the next run is still stale. **Suggested fix:** Change the warning and new docs to tell local-marketplace users to reinstall/refresh from the current checkout, or teach `/upgrade-larch` an explicit local-checkout refresh mode and only recommend it when it actually installs the working-tree version.
- **Suggested revision**: Address the concern above.


### FINDING_40: risk-integration: scripts/test-check-stale-plugin.sh:62-126
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Missing coverage for several documented skip branches WT plugin.json missing, unset CLAUDE_PLUGIN_ROOT path, bad git root, etc. can regress without failing CI Add focused temp-dir cases for each STALE_PLUGIN_CHECK=skip branch
- **Suggested revision**: Address the concern above.


