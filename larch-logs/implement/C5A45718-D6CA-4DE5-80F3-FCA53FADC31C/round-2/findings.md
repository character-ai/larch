### FINDING_1: [OUT_OF_SCOPE] code-quality: scripts/sanitize-mermaid-fragment.sh:283
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] REASON_TOKEN aggregation still uses awk -F'[ =]' while generate-code-flow-diagram.sh now preserves embedded = in SKIP_REASON. A hypothetical token REASON_TOKEN=foo=bar would parse as foo in warnings aggregation but foo=bar in SKIP_REASON, desyncing operator-facing skip reason vs execution-issues warning text. Align token extraction when sanitize-mermaid-fragment.sh is next touched, or via the planned shared-helper OOS issue.
- **Suggested revision**: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] architecture: scripts/ci-failed-jobs.sh:125-128
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Failed job names in TSV/KV emits are outside Item B stderr passthrough scope. Crafted matrix job names with control bytes could still affect TSV consumers; stderr path is hardened only. Address under OOS #2876 per design triage; do not expand this PR.
- **Suggested revision**: Address the concern above.

### FINDING_3: correctness: skills/implement/scripts/test-generate-code-flow-diagram.sh:72-76
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Plan documents empty REASON_TOKEN= behavior but harness does not regression-test it. Future awk change could break empty SKIP_REASON= contract without failing CI while other Item A cases pass. Add SANITIZE_REASON_LINE=REASON_TOKEN= case with assert_has_line SKIP_REASON=.
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] correctness: scripts/sanitize-mermaid-fragment.sh:283
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Warnings path still uses awk -F'[ =]' unlike new SKIP_REASON extractor. Hypothetical embedded= token would desync warnings text vs SKIP_REASON KV. Align token extraction when sanitize-mermaid-fragment.sh is next edited.
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] correctness: skills/implement/scripts/step-7a.sh:356-359
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] step-7a does not consume SKIP_REASON from generator output. Operators never see sanitizer REASON_TOKEN in summary skip text. Wire kv_value SKIP_REASON into CODE_FLOW_SKIP_REASON in a follow-up.
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] security: scripts/ci-failed-jobs.sh:106-153
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Stdout job-name path not covered by sanitize_diagnostic_line. Crafted job/matrix names with control bytes could affect TSV or KV lists (OOS_3). Track under OOS_3 per plan.
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] risk-integration: branch:1951c3e5
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Unrelated sentinel-validation and SECURITY.md changes bundled in version-bump commit. Reviewers may conflate #2854 scope with #2879 hardening. Split or call out stacked scope in PR body.
- **Suggested revision**: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: - **risk-integration** `scripts/test-ci-failed-jobs.sh` — Plan defers UTF-8/multi-byte preservation for `sanitize_diagnostic_line` to manual macOS verification; T8 covers BEL/ESC only. Acceptable per plan scope, but CI will not catch a future `LC_ALL=C` regression on UTF-8 passthrough. **Suggested fix:** optional follow-up harness case with a UTF-8 fixture (e.g. `éè`) asserting byte preservation after `tr -d '[:cntrl:]'`.
- **Suggested revision**: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: - **risk-integration** `scripts/ci-failed-jobs.sh:125-128` — TSV/KV job-name sanitization remains untested here (filed OOS_3 in plan). Pre-existing boundary, not introduced by this branch.
- **Suggested revision**: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: - **risk-integration** `scripts/test-ci-failed-jobs.sh:174-195` — Newline-driven stderr splitting is explicitly out of scope; no embedded-newline negative test (per plan FINDING_6/21/24). Documented in `ci-failed-jobs.md`; not a gap vs acceptance.
- **Suggested revision**: Address the concern above.

### FINDING_11: **Item A** (`generate-code-flow-diagram.sh:102`): Portable awk now extracts the token between `REASON_TOKEN=` and the first whitespace, preserving embedded `=` while dropping `fence=` / `line=` metadata. `REASON_TOKEN` values in `sanitize-mermaid-fragment.sh` are fixed literals, not user-derived, so the trust boundary is appropriate. `emit_kv` still has no newline escaping, but that was already true and is not worsened by this diff.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Item A** (`generate-code-flow-diagram.sh:102`): Portable awk now extracts the token between `REASON_TOKEN=` and the first whitespace, preserving embedded `=` while dropping `fence=` / `line=` metadata. `REASON_TOKEN` values in `sanitize-mermaid-fragment.sh` are fixed literals, not user-derived, so the trust boundary is appropriate. `emit_kv` still has no newline escaping, but that was already true and is not worsened by this diff.
- **Suggested revision**: Address the concern above.

### FINDING_12: **Item B** (`ci-failed-jobs.sh:29-33,86`): `sanitize_diagnostic_line` with `LC_ALL=C tr -d '[:cntrl:]'` plus `printf '%s'` before `larch_err` closes the control-byte / format-string edge on the only untrusted stderr passthrough site. KV emits at 152–153 remain on strict `sanitize_list` and are unchanged.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Item B** (`ci-failed-jobs.sh:29-33,86`): `sanitize_diagnostic_line` with `LC_ALL=C tr -d '[:cntrl:]'` plus `printf '%s'` before `larch_err` closes the control-byte / format-string edge on the only untrusted stderr passthrough site. KV emits at 152–153 remain on strict `sanitize_list` and are unchanged.
- **Suggested revision**: Address the concern above.

### FINDING_13: **Tests**: T8 and the three Item A harness cases exercise the intended contracts without widening production attack surface.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Tests**: T8 and the three Item A harness cases exercise the intended contracts without widening production attack surface. ---
- **Suggested revision**: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **security** `scripts/ci-failed-jobs.sh:106-135,152-153` — Failed-job names from `gh` stdout still reach TSV rows and `emit`/`emit_kv` lists without `sanitize_diagnostic_line`; only the stderr failure path is hardened. A crafted matrix job name with embedded newlines or control bytes could still pollute TSV/KV consumers. This is pre-existing, explicitly deferred as OOS_3 in the plan, and not introduced by Item B. **Suggested fix:** Track under OOS_3: apply a job-name allowlist sanitizer (or extend `sanitize_list`) on stdout-derived names before TSV/KV emit.
- **Suggested revision**: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 2. **security** `scripts/ci-failed-jobs.sh:85-87` — Newline-driven log-line splitting from `gh` stderr remains possible: `read -r` splits on `\n` before `sanitize_diagnostic_line` runs, so extra `larch_err` lines can still be injected via embedded newlines in stderr. The plan documents this as out of scope; the change reduces intra-line BEL/ESC/ANSI risk but does not remove multi-line injection. **Suggested fix:** Escalate via the documented OOS audit path if stronger gh-stderr boundaries are required (e.g., stream-level caps or collapsing).
- **Suggested revision**: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 3. **security** `scripts/get-issue-state.sh:49-51`, `scripts/tracking-issue-read.sh:5675-5735` — Bundled defense-in-depth: numeric `--issue` validation and sentinel `ISSUE_NUMBER`/`RUN_ID` validation with fixed-token errors reduce KV-injection and `gh` interpolation risk. Positive hardening, not part of #2854 scope. **Suggested fix:** None required for #2854; keep in PR if intentional bundle or split for review clarity.
- **Suggested revision**: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 4. **security** `skills/implement/scripts/generate-code-flow-diagram.sh:102` — `SKIP_REASON` is emitted via `emit_kv` without control-byte stripping (unlike Item B). Acceptable today because sanitizer tokens are fixed identifiers, but a poisoned `$sanitize_log` could still emit C0 bytes into the FD3 KV stream. Pre-existing trust model; not amplified. **Suggested fix:** Optional follow-up: pipe the awk output through the same `LC_ALL=C tr -d '[:cntrl:]'` helper for parity with Item B. --- **Summary:** The branch implements the planned sanitization correctly from a security lens. No blocking or in-scope regressions; residual exposure on the success-path job-name surface and newline-split stderr remain documented out-of-scope follow-ups.
- **Suggested revision**: Address the concern above.

### FINDING_18: risk-integration: scripts/ci-failed-jobs.sh:85-88
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Under set -euo pipefail a failing printf|sanitize_diagnostic_line pipeline aborts the stderr relay loop before exit 1. Rare tr failure mid-loop yields partial gh stderr relay and a non-guaranteed exit code instead of the documented gh-failure exit 1. Wrap sanitization with set +e or capture rc separately; finish the read loop then exit 1 explicitly.
- **Suggested revision**: Address the concern above.

### FINDING_19: correctness: skills/implement/scripts/test-generate-code-flow-diagram.sh:72-76
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] No harness case covers empty REASON_TOKEN= despite plan edge-case documentation. Future awk regressions could break empty-token SKIP_REASON= contract without failing CI. Add SANITIZE_REASON_LINE=REASON_TOKEN= case asserting SKIP_REASON= via assert_has_line.
- **Suggested revision**: Address the concern above.

### FINDING_20: [OUT_OF_SCOPE] security: scripts/ci-failed-jobs.sh:106-153
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Job names on stdout path remain outside sanitize_diagnostic_line scope. Crafted matrix/job names with control bytes could still affect TSV or KV lists (filed OOS_3). Track under OOS_3; apply stricter sanitization at TSV/KV emit if triaged.
- **Suggested revision**: Address the concern above.

### FINDING_21: [OUT_OF_SCOPE] correctness: skills/implement/scripts/step-7a.sh:356-359
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] step-7a ignores SKIP_REASON KV from the generator. Operators never see sanitizer REASON_TOKEN in summary skip text even after Item A fix. Wire kv_value SKIP_REASON into CODE_FLOW_SKIP_REASON when integrating step-7a (separate change).
- **Suggested revision**: Address the concern above.

### FINDING_22: [OUT_OF_SCOPE] correctness: scripts/sanitize-mermaid-fragment.sh:283
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Warnings token aggregation still splits REASON_TOKEN on spaces and equals. Hypothetical embedded= tokens would be truncated in issue warnings append path. Align warnings awk with the new portable extractor when tokens evolve.
- **Suggested revision**: Address the concern above.

### FINDING_23: [OUT_OF_SCOPE] risk-integration: SECURITY.md:133
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] SECURITY.md sentinel-validation text is unrelated to #2854 shell hardening. Reviewers may assume SECURITY.md delta is part of sanitization scope. Split unrelated SECURITY.md changes into a separate commit/PR or call out in PR body.
- **Suggested revision**: Address the concern above.

### FINDING_24: correctness: skills/implement/scripts/generate-code-flow-diagram.sh:102
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Implementation uses sub(/[[:space:]].*$/, "") instead of acceptance-specified sub(/ .*$/, ""). Acceptance checklist quotes the space-only awk literally; reviewers auditing checkbox-by-checkbox will flag a mismatch even though behavior matches plan prose for normal space-separated sanitizer lines. Align the second sub with acceptance (sub(/ .*$/, "")) or update the plan acceptance text to authorize [[:space:]].
- **Suggested revision**: Address the concern above.

