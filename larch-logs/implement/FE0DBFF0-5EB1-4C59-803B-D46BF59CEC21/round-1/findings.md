### FINDING_1: **correctness** `scripts/check-stale-plugin.sh:77-83` — `extract_version` runs `grep '"version"' "$1"` under `set -euo pipefail`, so a missing `"version"` field, an unreadable file, or any `grep` non-match aborts the whole script with exit status 1, which contradicts the header contract that normal output “always exits 0” (lines 18–25) and means the comparison/skip branches after lines 85–88 are never reached in those cases. **Suggested fix:** Make version extraction failure non-fatal inside the function (for example tolerate `grep` failure with `|| true`, or use `if grep …; then …; else printf ''; fi`), then treat an empty extracted version as `STALE_PLUGIN_CHECK=skip` so the helper truly always exits 0 for benign or malformed `plugin.json` inputs.
- **Reviewer**: dyn-session-wiring-output.txt
- **Concern**: - **correctness** `scripts/check-stale-plugin.sh:77-83` — `extract_version` runs `grep '"version"' "$1"` under `set -euo pipefail`, so a missing `"version"` field, an unreadable file, or any `grep` non-match aborts the whole script with exit status 1, which contradicts the header contract that normal output “always exits 0” (lines 18–25) and means the comparison/skip branches after lines 85–88 are never reached in those cases. **Suggested fix:** Make version extraction failure non-fatal inside the function (for example tolerate `grep` failure with `|| true`, or use `if grep …; then …; else printf ''; fi`), then treat an empty extracted version as `STALE_PLUGIN_CHECK=skip` so the helper truly always exits 0 for benign or malformed `plugin.json` inputs.
- **Suggested revision**: Address the concern above.

### FINDING_2: **correctness** `scripts/check-stale-plugin.sh:77-88` — With `set -euo pipefail`, `extract_version` runs `grep '"version"' "$1" | head -1 | sed …`; if `grep` finds no match it exits 1 and, under `pipefail`, the pipeline’s non-zero status can abort the whole script before the intended `[ -z "$INSTALLED_VERSION" ] || [ -z "$WT_VERSION" ]` branch runs, so the advertised “always exits 0” behavior and graceful `skip` handling for missing/parseable version fields are not guaranteed. **Suggested fix:** Stop the pipeline from failing on “no match” (for example append `|| true` to `grep`, use `grep … || :` before `sed`, or temporarily `set +e` around the extraction) so empty `INSTALLED_VERSION`/`WT_VERSION` reliably falls through to the existing `skip` logic.
- **Reviewer**: dyn-bash32-portability-output.txt
- **Concern**: - **correctness** `scripts/check-stale-plugin.sh:77-88` — With `set -euo pipefail`, `extract_version` runs `grep '"version"' "$1" | head -1 | sed …`; if `grep` finds no match it exits 1 and, under `pipefail`, the pipeline’s non-zero status can abort the whole script before the intended `[ -z "$INSTALLED_VERSION" ] || [ -z "$WT_VERSION" ]` branch runs, so the advertised “always exits 0” behavior and graceful `skip` handling for missing/parseable version fields are not guaranteed. **Suggested fix:** Stop the pipeline from failing on “no match” (for example append `|| true` to `grep`, use `grep … || :` before `sed`, or temporarily `set +e` around the extraction) so empty `INSTALLED_VERSION`/`WT_VERSION` reliably falls through to the existing `skip` logic.
- **Suggested revision**: Address the concern above.

### FINDING_3: **risk-integration** `scripts/session-setup.sh:207-212` — The stale check is invoked as `_stale_out=$("$SCRIPT_DIR/check-stale-plugin.sh" 2>/dev/null || true)`, which intentionally prevents `session-setup.sh` from failing when the helper exits non-zero and also discards the helper’s stderr; combined with the `grep`/`set -e` hazard above, a skew warning can be dropped with no operator-visible diagnostic, and even after hardening the helper this wrapper still hides genuine stderr-only failures (for example unexpected aborts) unless you add an explicit `larch_err`/breadcrumb path. **Suggested fix:** First harden `check-stale-plugin.sh` so non-zero exits are unexpected, then either remove `2>/dev/null` for the happy path or map `rc!=0` to a single `larch_err` line (still exiting 0 from `session-setup.sh`) so “warn-only” does not mean “silent.”
- **Reviewer**: dyn-session-wiring-output.txt
- **Concern**: - **risk-integration** `scripts/session-setup.sh:207-212` — The stale check is invoked as `_stale_out=$("$SCRIPT_DIR/check-stale-plugin.sh" 2>/dev/null || true)`, which intentionally prevents `session-setup.sh` from failing when the helper exits non-zero and also discards the helper’s stderr; combined with the `grep`/`set -e` hazard above, a skew warning can be dropped with no operator-visible diagnostic, and even after hardening the helper this wrapper still hides genuine stderr-only failures (for example unexpected aborts) unless you add an explicit `larch_err`/breadcrumb path. **Suggested fix:** First harden `check-stale-plugin.sh` so non-zero exits are unexpected, then either remove `2>/dev/null` for the happy path or map `rc!=0` to a single `larch_err` line (still exiting 0 from `session-setup.sh`) so “warn-only” does not mean “silent.”
- **Suggested revision**: Address the concern above.

### FINDING_4: **risk-integration** `scripts/session-setup.sh:212` — The warning points dev-clone users at `/larch:upgrade-larch`, but `skills/upgrade-larch/scripts/upgrade-larch.sh:234-238` re-adds the GitHub marketplace and installs the latest stable release, not the current working tree; `docs/skills.md:201` also says local-checkout users should not use that flow. Concrete scenario: a local clone has unreleased working-tree version `29.8.40` and the cache has stable `29.8.39`; the warning fires, `/larch:upgrade-larch` reinstalls or no-ops at GitHub stable `29.8.39`, and the next run is still stale. **Suggested fix:** Change the warning and new docs to tell local-marketplace users to reinstall/refresh from the current checkout, or teach `/upgrade-larch` an explicit local-checkout refresh mode and only recommend it when it actually installs the working-tree version.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: - **risk-integration** `scripts/session-setup.sh:212` — The warning points dev-clone users at `/larch:upgrade-larch`, but `skills/upgrade-larch/scripts/upgrade-larch.sh:234-238` re-adds the GitHub marketplace and installs the latest stable release, not the current working tree; `docs/skills.md:201` also says local-checkout users should not use that flow. Concrete scenario: a local clone has unreleased working-tree version `29.8.40` and the cache has stable `29.8.39`; the warning fires, `/larch:upgrade-larch` reinstalls or no-ops at GitHub stable `29.8.39`, and the next run is still stale. **Suggested fix:** Change the warning and new docs to tell local-marketplace users to reinstall/refresh from the current checkout, or teach `/upgrade-larch` an explicit local-checkout refresh mode and only recommend it when it actually installs the working-tree version.
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] **Awk parsing:** For the script’s actual `KEY=value` lines (no embedded `=` in semver values), `awk -F=` with `$2` and `END { print v }` behaves predictably on empty capture (blank `_stale_check`, no warning branch) and on the normal three-line stdout bundle from `working-tree-ahead`.
- **Reviewer**: dyn-session-wiring-output.txt
- **Concern**: - **Awk parsing:** For the script’s actual `KEY=value` lines (no embedded `=` in semver values), `awk -F=` with `$2` and `END { print v }` behaves predictably on empty capture (blank `_stale_check`, no warning branch) and on the normal three-line stdout bundle from `working-tree-ahead`.
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] **Same-directory / `--plugin-dir` case:** When `CLAUDE_PLUGIN_ROOT` points at the working tree, `check-stale-plugin.sh` reads the same `.claude-plugin/plugin.json` for both installed and working-tree roots (via `git rev-parse --show-toplevel`), so extracted versions should match and `STALE_PLUGIN_CHECK` should resolve to `versions-match`, avoiding a false `working-tree-ahead` warning by design (`scripts/check-stale-plugin.sh:48-48` vs `71-71`, comparison `107-121`).
- **Reviewer**: dyn-session-wiring-output.txt
- **Concern**: - **Same-directory / `--plugin-dir` case:** When `CLAUDE_PLUGIN_ROOT` points at the working tree, `check-stale-plugin.sh` reads the same `.claude-plugin/plugin.json` for both installed and working-tree roots (via `git rev-parse --show-toplevel`), so extracted versions should match and `STALE_PLUGIN_CHECK` should resolve to `versions-match`, avoiding a false `working-tree-ahead` warning by design (`scripts/check-stale-plugin.sh:48-48` vs `71-71`, comparison `107-121`).
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] **`emit` wiring:** The warning uses `emit` with a single formatted string, matching `emit()` in `scripts/lib-quiet.sh:97-103` and the existing `emit "$PREFLIGHT_OUTPUT"` pattern in `scripts/session-setup.sh:197-197`, so the call shape is consistent with the quiet/contract stream conventions.
- **Reviewer**: dyn-session-wiring-output.txt
- **Concern**: - **`emit` wiring:** The warning uses `emit` with a single formatted string, matching `emit()` in `scripts/lib-quiet.sh:97-103` and the existing `emit "$PREFLIGHT_OUTPUT"` pattern in `scripts/session-setup.sh:197-197`, so the call shape is consistent with the quiet/contract stream conventions.
- **Suggested revision**: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] correctness
- **Reviewer**: dyn-bash32-portability-output.txt
- **Concern**: - **correctness** `scripts/session-setup.sh:207` — Wrapping `"$SCRIPT_DIR/check-stale-plugin.sh"` in `… || true` avoids aborting session setup if `check-stale-plugin.sh` ever exits non-zero, but it also means any future hard failure in that helper (including the `grep`/`pipefail` case above) becomes a silent no-op for the stale-plugin warning; tightening `check-stale-plugin.sh` to always exit 0 on benign inputs remains the better fix, with this wrapper as a secondary safety net only.
- **Suggested revision**: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] No Bash 4+ constructs (`declare -A`/`declare -n`, `mapfile`/`readarray`, `${var^^}`/`${var,,}`, `&>>`, `coproc`) appear in the new or modified shell hunks in `scripts/check-stale-plugin.sh`, `scripts/test-check-stale-plugin.sh`, or the inserted block in `scripts/session-setup.sh`; `local`, `[[ … ]]`, `$()`, `${param//pat/repl}`, `${param:0:32}`, and the embedded `awk` (ternary, `split`) are consistent with macOS Bash 3.2 and typical BSD `awk`.
- **Reviewer**: dyn-bash32-portability-output.txt
- **Concern**: - No Bash 4+ constructs (`declare -A`/`declare -n`, `mapfile`/`readarray`, `${var^^}`/`${var,,}`, `&>>`, `coproc`) appear in the new or modified shell hunks in `scripts/check-stale-plugin.sh`, `scripts/test-check-stale-plugin.sh`, or the inserted block in `scripts/session-setup.sh`; `local`, `[[ … ]]`, `$()`, `${param//pat/repl}`, `${param:0:32}`, and the embedded `awk` (ternary, `split`) are consistent with macOS Bash 3.2 and typical BSD `awk`.
- **Suggested revision**: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] correctness: scripts/session-setup.sh:195-198
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Preflight output is already re-emitted through emit on failure Behavior predates this diff; not introduced by stale-plugin work None required for this review scope
- **Suggested revision**: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] correctness: skills/fix-issue/SKILL.md (unchanged)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Feature description says fix-issue Step 0; skill uses Step 1 for session-setup Stakeholder-facing wording mismatch only; implementation follows implementation plan None in this PR; update feature text or skill docs separately if desired
- **Suggested revision**: Address the concern above.

### FINDING_12: architecture: scripts/check-stale-plugin.sh:18-36
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Doc says always exit 0 unknown option exits 1 Direct invokers or tests see exit 1 vs documented warn-only exit 0 Document diagnostic exit or make unknown options soft-fail at exit 0
- **Suggested revision**: Address the concern above.

### FINDING_13: architecture: scripts/session-setup.sh:212 docs/installation-and-setup.md:242-248
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] emit used vs stated stderr warning Quiet sessions route emit to FD3 not literal stderr Also larch_err or reword docs to contract-visible
- **Suggested revision**: Address the concern above.

### FINDING_14: code-quality: docs/installation-and-setup.md:30-34,64-75
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Mixed slash-command spellings /upgrade-larch vs /larch:upgrade-larch Users may try the wrong token in an environment that only exposes one form Use one canonical spelling or note they are equivalent
- **Suggested revision**: Address the concern above.

### FINDING_15: code-quality: docs/installation-and-setup.md:75
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Overclaims once per session and any larch skill Misleading expectations for skills that skip session-setup or for multiple setup calls in one Claude session Rephrase to per session-setup and name representative skills
- **Suggested revision**: Address the concern above.

### FINDING_16: code-quality: docs/linting.md (missing)
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] New harness not listed beside peers like test-check-clean-tree Contributors relying on docs/linting.md may not discover make test-check-stale-plugin Add a table row mirroring other script harness entries
- **Suggested revision**: Address the concern above.

### FINDING_17: code-quality: feature_description vs scripts/session-setup.sh:212
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Feature text says stderr; implementation uses emit (FD3) for visibility under lib-quiet Future “fix” might move message to stderr and hide it in quiet sessions Align requirement wording with emit-based visibility or note rationale in docs
- **Suggested revision**: Address the concern above.

### FINDING_18: code-quality: scripts/check-stale-plugin.md:1-3
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Contract claims always exit 0 but script exits 1 on unknown CLI Operators reading the contract may assume argv mistakes are also warn-only Qualify exit 0 to detection-only outcomes; document exit 1 for argv errors
- **Suggested revision**: Address the concern above.

### FINDING_19: code-quality: scripts/check-stale-plugin.sh:328-336
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Header claims always exit 0 but unknown flags exit 1 Typo flags yield exit 1 despite warn-only framing in comments Clarify comment or map bad-args to skip with exit 0
- **Suggested revision**: Address the concern above.

### FINDING_20: correctness: docs/installation-and-setup.md:75
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Doc claims warning fires once per session Operators may expect a single warning per Claude session but see repeats whenever session-setup runs again Reword to per session-setup invocation or define session precisely
- **Suggested revision**: Address the concern above.

### FINDING_21: correctness: feature_description vs skills/fix-issue/SKILL.md:118
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Feature text says /fix-issue Step 0 but session-setup runs in Step 1 Operators search Step 0 for a warning that is emitted during Step 1 setup Update feature/issue wording to match SKILL step numbering
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

### FINDING_26: correctness: scripts/check-stale-plugin.sh:387-398
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] extract_version is first-match grep on any line containing the substring version Wrong or empty semver if an earlier JSON line also contains a version token, misclassifying skew Use jq when available or stricter top-level parsing
- **Suggested revision**: Address the concern above.

### FINDING_27: correctness: scripts/check-stale-plugin.sh:77-83
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Grep-based version extraction uses the first "version" match Version skew detection can be wrong or misleading for unusual JSON ordering Tighten the pattern or document/limit the JSON shape assumed
- **Suggested revision**: Address the concern above.

### FINDING_28: correctness: scripts/check-stale-plugin.sh:77-88
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] extract_version uses grep in a pipefail pipeline When plugin.json has no matching "version" line grep exits 1 the whole script aborts non-zero session-setup masks with || true so skew is silent and contract says exit 0 Make grep non-fatal treat empty version as skip add harness align exit contract
- **Suggested revision**: Address the concern above.

### FINDING_29: correctness: scripts/check-stale-plugin.sh:90-105
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Awk numeric coercion mangles non-numeric semver tails If versions ever include pre-release tokens, ordering may be wrong Compare numeric triples only or adopt repo semver policy
- **Suggested revision**: Address the concern above.

### FINDING_30: correctness: scripts/check-stale-plugin.sh:93-104
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] version_cmp compares only three semver segments Fourth segment differences compare as equal skew or match signals wrong Document 3-tuple limit or compare all split segments up to a cap
- **Suggested revision**: Address the concern above.

### FINDING_31: correctness: scripts/session-setup.sh:207
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] stderr from check-stale-plugin.sh is discarded entirely Real failures can hide completely and the version-skew warning never appears with no explanation Stop redirecting stderr to /dev/null or only suppress known-safe noise
- **Suggested revision**: Address the concern above.

### FINDING_32: correctness: scripts/session-setup.sh:207-212
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Warning uses emit (FD3) not stderr (FD4) per lib-quiet semantics Automation or tooling that only captures stderr never sees the version-skew banner despite STALE_PLUGIN_CHECK=working-tree-ahead Use larch_err/larch_errf for the banner or align docs/requirements with emit-based visibility
- **Suggested revision**: Address the concern above.

### FINDING_33: risk-integration: docs/installation-and-setup.md:235-250
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Documents a stderr warning but implementation uses emit (stdout/FD3 per lib-quiet) Operators look on stderr and miss guidance; docs disagree with runtime behavior Align wording with emit / Bash tool visibility
- **Suggested revision**: Address the concern above.

### FINDING_34: risk-integration: docs/installation-and-setup.md:235-250
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Feature text says stderr; implementation uses emit/lib-quiet stream Acceptance wording mismatch; not a CI break unless stderr is mandatory Align docs/issue wording with emit contract or switch to larch_err if stderr required
- **Suggested revision**: Address the concern above.

### FINDING_35: risk-integration: scripts/session-setup.sh:206-213
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] check-stale-plugin wrapped in 2>/dev/null || true masks all failures and stderr from the helper Any non-zero exit or stderr from the checker (including pipefail from grep) is silently ignored while session setup continues Remove || true once helper is fail-soft on all detection paths; or on non-zero status emit a single larch_err instead of full silence
- **Suggested revision**: Address the concern above.

### FINDING_36: risk-integration: scripts/session-setup.sh:206-213
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] 2>/dev/null and || true swallow all helper failures Any non-zero exit from check-stale-plugin yields no warning and no diagnostic; skew check can fail silently Remove blanket masking after helper is hardened; optionally larch_err on unexpected rc
- **Suggested revision**: Address the concern above.

### FINDING_37: risk-integration: scripts/session-setup.sh:207
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] check-stale-plugin stderr redirected to /dev/null Real stderr diagnostics from check-stale-plugin are dropped silently Remove 2>/dev/null or tee stderr to the quiet log without hiding it entirely
- **Suggested revision**: Address the concern above.

### FINDING_38: risk-integration: scripts/session-setup.sh:207
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] stderr of check-stale-plugin discarded Future stderr diagnostics silently lost Remove 2>/dev/null or tee controlled stderr
- **Suggested revision**: Address the concern above.

### FINDING_39: risk-integration: scripts/test-check-stale-plugin.sh:1-126
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Plan testing strategy listed missing CLAUDE_PLUGIN_ROOT (and broadly missing plugin.json) but harness omits unset-env default path and WT plugin.json missing case Regression gap: default-env skip path and WT-missing skip are untested despite being named in the plan Add harness subprocess cases or trim the plan’s promised edge matrix
- **Suggested revision**: Address the concern above.

### FINDING_40: risk-integration: scripts/test-check-stale-plugin.sh:62-126
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Missing coverage for several documented skip branches WT plugin.json missing, unset CLAUDE_PLUGIN_ROOT path, bad git root, etc. can regress without failing CI Add focused temp-dir cases for each STALE_PLUGIN_CHECK=skip branch
- **Suggested revision**: Address the concern above.

### FINDING_41: risk-integration: scripts/test-check-stale-plugin.sh:62-126
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No integration test for session-setup warning wiring Regression could remove emit block without test failure Add harness or source-level contract test for session-setup stale-plugin path
- **Suggested revision**: Address the concern above.

### FINDING_42: security: scripts/session-setup.sh:206-212
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] plugin.json version strings are embedded in orchestrator-visible emit text without validation A compromised or malformed plugin.json could inject long or instruction-like text into the session banner consumed as operational context Validate semver (or strip/limit) before emitting; omit raw values when invalid
- **Suggested revision**: Address the concern above.

