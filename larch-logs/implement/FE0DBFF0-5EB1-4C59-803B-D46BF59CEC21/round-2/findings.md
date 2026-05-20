### FINDING_1: **risk-integration** `scripts/session-setup.sh:207-214` — The failure path uses `if ! _stale_out=$("$SCRIPT_DIR/check-stale-plugin.sh" 2>&1); then` followed by `_stale_rc=$?`. In Bash, a successful `if ! …` test leaves `$?` as `0` (the negated condition succeeded), not the helper’s exit status, so `larch_errf` logs `rc=0` even when `check-stale-plugin.sh` exited non-zero (for example invalid CLI usage or future `set -e` failures), which misreports diagnostics and weakens integration triage. **Suggested fix:** Initialize `_stale_rc=0`, assign with `_stale_out=$("$SCRIPT_DIR/check-stale-plugin.sh" 2>&1) || _stale_rc=$?`, then run the `larch_errf` / clear branch when `[[ $_stale_rc -ne 0 ]]` instead of relying on `$?` after `if !`.
- **Reviewer**: dyn-wiring-output.txt
- **Concern**: - **risk-integration** `scripts/session-setup.sh:207-214` — The failure path uses `if ! _stale_out=$("$SCRIPT_DIR/check-stale-plugin.sh" 2>&1); then` followed by `_stale_rc=$?`. In Bash, a successful `if ! …` test leaves `$?` as `0` (the negated condition succeeded), not the helper’s exit status, so `larch_errf` logs `rc=0` even when `check-stale-plugin.sh` exited non-zero (for example invalid CLI usage or future `set -e` failures), which misreports diagnostics and weakens integration triage. **Suggested fix:** Initialize `_stale_rc=0`, assign with `_stale_out=$("$SCRIPT_DIR/check-stale-plugin.sh" 2>&1) || _stale_rc=$?`, then run the `larch_errf` / clear branch when `[[ $_stale_rc -ne 0 ]]` instead of relying on `$?` after `if !`.
- **Suggested revision**: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] Merging stderr into the capture via `2>&1` is unlikely to break `KEY=value` parsing on the normal success path of `check-stale-plugin.sh` (stdout-only `emit_kv`); the main practical hazard there would be unexpected stderr on success, which the current helper does not emit.
- **Reviewer**: dyn-wiring-output.txt
- **Concern**: - Merging stderr into the capture via `2>&1` is unlikely to break `KEY=value` parsing on the normal success path of `check-stale-plugin.sh` (stdout-only `emit_kv`); the main practical hazard there would be unexpected stderr on success, which the current helper does not emit.
- **Suggested revision**: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] The product blurb in `<feature_description>` mentions a “stderr warning,” but the branch intentionally uses `emit` so the skew banner is visible on the orchestrator-facing stream (see `scripts/check-stale-plugin.md`); that is a wording vs. contract nuance, not a regression in the new wiring itself.
- **Reviewer**: dyn-wiring-output.txt
- **Concern**: - The product blurb in `<feature_description>` mentions a “stderr warning,” but the branch intentionally uses `emit` so the skew banner is visible on the orchestrator-facing stream (see `scripts/check-stale-plugin.md`); that is a wording vs. contract nuance, not a regression in the new wiring itself.
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] `larch_errf` is defined in `scripts/lib-quiet.sh` and is available at the call site because `session-setup.sh` sources that library before section 1a (`scripts/session-setup.sh:61-63`).
- **Reviewer**: dyn-wiring-output.txt
- **Concern**: - `larch_errf` is defined in `scripts/lib-quiet.sh` and is available at the call site because `session-setup.sh` sources that library before section 1a (`scripts/session-setup.sh:61-63`).
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] architecture: scripts/session-setup.sh:195-198
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Preflight failure path already re-emits arbitrary PREFLIGHT_OUTPUT via emit before exit. Not introduced by this diff; same stream has historically carried non-KV lines on failure. No change required for this review scope.
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] security: scripts/lib-quiet.sh:88-94
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] larch_errf uses printf "$@", which is unsafe if the format string is ever user-controlled. Pre-existing helper; new session-setup usage supplies a constant format string first, so it does not introduce the vulnerability. None required for this PR; any future hardening would belong in a dedicated lib-quiet change.
- **Suggested revision**: Address the concern above.

### FINDING_7: architecture: scripts/session-setup.sh:36-40,219-278
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Stale-plugin warning uses emit (FD3 / duplicated stdout) and injects non-KEY=value prose on the stream documented as KEY=value stdout; feature text asked for stderr. Automation or future wrappers that assume stdout is only parseable KEY=value (or that warnings are on stderr) can break or miss the banner; stderr requirement from feature tag is unmet. Emit warning via larch_err/larch_errf to FD4 or add machine-readable KV on stdout and prose on stderr; update session-setup header and session-setup.md contract.
- **Suggested revision**: Address the concern above.

### FINDING_8: code-quality: agent-lint.toml:1182-1184
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] check-stale-plugin.sh listed amid mostly .md sibling-contract paths. Slightly harder navigation for future editors. Regroup excludes for clarity only.
- **Suggested revision**: Address the concern above.

### FINDING_9: code-quality: scripts/check-stale-plugin.sh:84-95
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Grep-first-line version extraction is brittle if JSON gains multiple version keys. Rare mis-parse could skip or mis-compare versions. Tighten pattern or add jq if dependency acceptable later.
- **Suggested revision**: Address the concern above.

### FINDING_10: code-quality: scripts/session-setup.sh:215-218
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Three awk passes over the same string. Slightly higher complexity than needed for marginal cost. Single awk block or line parser.
- **Suggested revision**: Address the concern above.

### FINDING_11: code-quality: scripts/session-setup.sh:36-50
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Header claims stdout is KEY=value-only while markdown warnings are emitted. Readers mis-model parser expectations for session-setup stdout. Update header to mention optional human-readable lines.
- **Suggested revision**: Address the concern above.

### FINDING_12: code-quality: scripts/test-check-stale-plugin.sh:1-170
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Harness omits invalid CLI exit-1 cases documented in check-stale-plugin.md. CLI regressions would not be caught by CI. Add minimal negative tests for bad flags and missing values.
- **Suggested revision**: Address the concern above.

### FINDING_13: correctness: docs/installation-and-setup.md:75
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Doc claims the stale-plugin warning runs for /review alongside /implement and /fix-issue. /review calls session-setup with --skip-preflight, so the new check at scripts/session-setup.sh:207-221 is skipped; readers expect a warning that never appears on that path. Remove /review from the entrypoint list or document that only non-skip-preflight session-setup runs trigger the warning.
- **Suggested revision**: Address the concern above.

### FINDING_14: correctness: implementation_plan Goal vs scripts/session-setup.sh:219
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Plan Goal explicitly names /larch:upgrade-larch; on-screen emit string is generic reinstall/refresh wording. Operators skim the banner and never see the slash command the plan called out as the primary remediation cue. Mention /larch:upgrade-larch in the banner or doc example where accurate, keeping local-plugin-dir nuance in prose.
- **Suggested revision**: Address the concern above.

### FINDING_15: correctness: scripts/check-stale-plugin.sh:105-119
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] version_cmp compares only three dotted components and uses numeric coercion. Four-part versions or suffixed segments could compare equal when they should not, muting or misclassifying skew. Document X.Y.Z-only assumption or extend parsing/comparison.
- **Suggested revision**: Address the concern above.

### FINDING_16: correctness: scripts/check-stale-plugin.sh:105-119
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Awk three-segment numeric coercion mishandles prerelease or extra semver segments False ahead/behind or spurious match if non-numeric suffixes appear in version strings Document numeric X.Y.Z only as supported or reject non-conforming strings as skip
- **Suggested revision**: Address the concern above.

### FINDING_17: correctness: scripts/check-stale-plugin.sh:105-120
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Three-part numeric comparison ignores semver prerelease/extra segments and coerces non-numeric parts via awk +0. Unusual version strings could compare equal when semver says different, or order opposite to release semantics, muting or mis-firing the skew warning. Document supported version shape or parse semver subset strictly (reject non-numeric fields / strip prerelease).
- **Suggested revision**: Address the concern above.

### FINDING_18: correctness: scripts/check-stale-plugin.sh:122-135
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Empty or unexpected version_cmp output falls through to versions-match. A broken awk or unexpected output could hide working-tree-ahead skew. Default unknown/empty CMP to skip with stderr note instead of versions-match.
- **Suggested revision**: Address the concern above.

### FINDING_19: correctness: scripts/check-stale-plugin.sh:83-119
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Loose version parse + 3-part numeric awk compare ignores semver prerelease/extra segments and coerces non-numeric tails. Example: installed 1.0.0 vs WT 1.0.0-rc1 can yield versions-match (no warning) despite semver ordering; 1.0.0 vs 1.0.0.1 compares only three fields. Document limitations for warn-only Option A or switch to stricter version ordering if required.
- **Suggested revision**: Address the concern above.

### FINDING_20: correctness: scripts/check-stale-plugin.sh:84-95
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] extract_version uses first grep hit for the substring "version". Malformed or nested JSON could pick the wrong version token and emit a misleading working-tree-ahead or match result. Tighten the grep pattern to the plugin version key line or use structured JSON parsing.
- **Suggested revision**: Address the concern above.

### FINDING_21: correctness: scripts/session-setup.sh:219
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Feature text requires a stderr warning; code uses emit (FD3 / original stdout after quiet init), not larch_err to FD4 stderr. A wrapper or operator tailing only real stderr (FD2 after init) never sees the skew banner even though session-setup succeeds. Route the human banner via larch_err/larch_errf if stderr is mandatory; otherwise align the written requirement with emit/contract-stream semantics.
- **Suggested revision**: Address the concern above.

### FINDING_22: correctness: scripts/session-setup.sh:219 vs feature_description
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Feature text calls for a stderr warning; implementation uses emit (FD3 contract stream after lib-quiet), not stderr. Tooling or operators that only surface stderr could miss the banner while stdout/contract streams are suppressed differently. Align the spec with emit, or duplicate the banner to larch_err if stderr delivery is mandatory.
- **Suggested revision**: Address the concern above.

### FINDING_23: risk-integration: docs/installation-and-setup.md:75
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Doc claims /review is a typical entrypoint for the warning; /review passes --skip-preflight so the stale-plugin block never runs. Operators read that /review will surface the warning but it will not in the default skill flow. List only entrypoints that omit --skip-preflight or note the /review exception explicitly.
- **Suggested revision**: Address the concern above.

### FINDING_24: risk-integration: scripts/session-setup.sh:207-220
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No integration test for session-setup stale-plugin wiring Parsing or guard regression in session-setup could silence warnings while helper tests stay green Add minimal session-setup harness covering working-tree-ahead emit line
- **Suggested revision**: Address the concern above.

### FINDING_25: risk-integration: scripts/session-setup.sh:207-221
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Stale-plugin check is tied to SKIP_PREFLIGHT=false. Callers using --skip-preflight never run check-stale-plugin even in a larch dev clone with a stale cached plugin, so the protection is absent on those paths. Decouple with a separate opt-out or document that --skip-preflight also skips skew detection.
- **Suggested revision**: Address the concern above.

### FINDING_26: risk-integration: scripts/session-setup.sh:215-219
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Unvalidated version strings from plugin.json are embedded in the session-setup emit banner visible to the orchestrator. A compromised or maliciously edited manifest supplies a version field containing markdown or instruction-like text that merges with the warning and influences how the host model interprets subsequent transcript content. Validate version against a strict numeric semver pattern before emitting, or omit raw values from the banner.
- **Suggested revision**: Address the concern above.

### FINDING_27: risk-integration: scripts/session-setup.sh:219
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Skew banner uses emit (restored stdout / FD3), not stderr, vs feature text calling for stderr. Monitoring or wrappers that only tail stderr never see the skew banner though the orchestrator sees contract stdout. Align wording with behavior or emit the banner via larch_errf if stderr is required.
- **Suggested revision**: Address the concern above.

### FINDING_28: risk-integration: scripts/session-setup.sh:219
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Warn path uses emit (FD3 contract stream) not stderr as stated in feature text External wrappers or operators grepping only FD2 for the skew banner can miss the warning while CI still passes Use larch_err for human banner or revise acceptance to contract-stream visibility
- **Suggested revision**: Address the concern above.

### FINDING_29: risk-integration: scripts/test-check-stale-plugin.sh:1-170
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] No harness for invalid CLI exit 1 documented in check-stale-plugin.md Bad-argv behavior could regress to exit 0 without failing CI Add unknown-flag and missing-value micro-tests asserting rc=1
- **Suggested revision**: Address the concern above.

### FINDING_30: risk-integration: scripts/test-check-stale-plugin.sh:138-146
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Missing working-tree manifest missing-version case unlike installed case7 Silent skip on malformed WT version field less regression-safe than installed path Add symmetric case asserting skip when WT plugin.json lacks version
- **Suggested revision**: Address the concern above.

### FINDING_31: security: scripts/check-stale-plugin.sh:84-86
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] grep is invoked without '--' before the file operand. A path of '-' makes grep read stdin, so version detection can silently ignore the intended file or consume unintended input. Use grep -F (or fixed-string mode) with '--' before the path argument.
- **Suggested revision**: Address the concern above.

