### FINDING_1: [OUT_OF_SCOPE] code-quality: scripts/sanitize-mermaid-fragment.sh:283
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] REASON_TOKEN aggregation still uses awk -F'[ =]' while generate-code-flow-diagram.sh now preserves embedded = in SKIP_REASON. A hypothetical token REASON_TOKEN=foo=bar would parse as foo in warnings aggregation but foo=bar in SKIP_REASON, desyncing operator-facing skip reason vs execution-issues warning text. Align token extraction when sanitize-mermaid-fragment.sh is next touched, or via the planned shared-helper OOS issue.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_10: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: - **risk-integration** `scripts/test-ci-failed-jobs.sh:174-195` — Newline-driven stderr splitting is explicitly out of scope; no embedded-newline negative test (per plan FINDING_6/21/24). Documented in `ci-failed-jobs.md`; not a gap vs acceptance.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_14: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **security** `scripts/ci-failed-jobs.sh:106-135,152-153` — Failed-job names from `gh` stdout still reach TSV rows and `emit`/`emit_kv` lists without `sanitize_diagnostic_line`; only the stderr failure path is hardened. A crafted matrix job name with embedded newlines or control bytes could still pollute TSV/KV consumers. This is pre-existing, explicitly deferred as OOS_3 in the plan, and not introduced by Item B. **Suggested fix:** Track under OOS_3: apply a job-name allowlist sanitizer (or extend `sanitize_list`) on stdout-derived names before TSV/KV emit.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_15: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 2. **security** `scripts/ci-failed-jobs.sh:85-87` — Newline-driven log-line splitting from `gh` stderr remains possible: `read -r` splits on `\n` before `sanitize_diagnostic_line` runs, so extra `larch_err` lines can still be injected via embedded newlines in stderr. The plan documents this as out of scope; the change reduces intra-line BEL/ESC/ANSI risk but does not remove multi-line injection. **Suggested fix:** Escalate via the documented OOS audit path if stronger gh-stderr boundaries are required (e.g., stream-level caps or collapsing).
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_16: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 3. **security** `scripts/get-issue-state.sh:49-51`, `scripts/tracking-issue-read.sh:5675-5735` — Bundled defense-in-depth: numeric `--issue` validation and sentinel `ISSUE_NUMBER`/`RUN_ID` validation with fixed-token errors reduce KV-injection and `gh` interpolation risk. Positive hardening, not part of #2854 scope. **Suggested fix:** None required for #2854; keep in PR if intentional bundle or split for review clarity.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_17: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 4. **security** `skills/implement/scripts/generate-code-flow-diagram.sh:102` — `SKIP_REASON` is emitted via `emit_kv` without control-byte stripping (unlike Item B). Acceptable today because sanitizer tokens are fixed identifiers, but a poisoned `$sanitize_log` could still emit C0 bytes into the FD3 KV stream. Pre-existing trust model; not amplified. **Suggested fix:** Optional follow-up: pipe the awk output through the same `LC_ALL=C tr -d '[:cntrl:]'` helper for parity with Item B. --- **Summary:** The branch implements the planned sanitization correctly from a security lens. No blocking or in-scope regressions; residual exposure on the success-path job-name surface and newline-split stderr remain documented out-of-scope follow-ups.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_2: [OUT_OF_SCOPE] architecture: scripts/ci-failed-jobs.sh:125-128
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Failed job names in TSV/KV emits are outside Item B stderr passthrough scope. Crafted matrix job names with control bytes could still affect TSV consumers; stderr path is hardened only. Address under OOS #2876 per design triage; do not expand this PR.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_20: [OUT_OF_SCOPE] security: scripts/ci-failed-jobs.sh:106-153
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Job names on stdout path remain outside sanitize_diagnostic_line scope. Crafted matrix/job names with control bytes could still affect TSV or KV lists (filed OOS_3). Track under OOS_3; apply stricter sanitization at TSV/KV emit if triaged.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_21: [OUT_OF_SCOPE] correctness: skills/implement/scripts/step-7a.sh:356-359
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] step-7a ignores SKIP_REASON KV from the generator. Operators never see sanitizer REASON_TOKEN in summary skip text even after Item A fix. Wire kv_value SKIP_REASON into CODE_FLOW_SKIP_REASON when integrating step-7a (separate change).
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_22: [OUT_OF_SCOPE] correctness: scripts/sanitize-mermaid-fragment.sh:283
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Warnings token aggregation still splits REASON_TOKEN on spaces and equals. Hypothetical embedded= tokens would be truncated in issue warnings append path. Align warnings awk with the new portable extractor when tokens evolve.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_23: [OUT_OF_SCOPE] risk-integration: SECURITY.md:133
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] SECURITY.md sentinel-validation text is unrelated to #2854 shell hardening. Reviewers may assume SECURITY.md delta is part of sanitization scope. Split unrelated SECURITY.md changes into a separate commit/PR or call out in PR body.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_4: [OUT_OF_SCOPE] correctness: scripts/sanitize-mermaid-fragment.sh:283
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Warnings path still uses awk -F'[ =]' unlike new SKIP_REASON extractor. Hypothetical embedded= token would desync warnings text vs SKIP_REASON KV. Align token extraction when sanitize-mermaid-fragment.sh is next edited.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_5: [OUT_OF_SCOPE] correctness: skills/implement/scripts/step-7a.sh:356-359
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] step-7a does not consume SKIP_REASON from generator output. Operators never see sanitizer REASON_TOKEN in summary skip text. Wire kv_value SKIP_REASON into CODE_FLOW_SKIP_REASON in a follow-up.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_6: [OUT_OF_SCOPE] security: scripts/ci-failed-jobs.sh:106-153
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Stdout job-name path not covered by sanitize_diagnostic_line. Crafted job/matrix names with control bytes could affect TSV or KV lists (OOS_3). Track under OOS_3 per plan.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_7: [OUT_OF_SCOPE] risk-integration: branch:1951c3e5
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Unrelated sentinel-validation and SECURITY.md changes bundled in version-bump commit. Reviewers may conflate #2854 scope with #2879 hardening. Split or call out stacked scope in PR body.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_8: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: - **risk-integration** `scripts/test-ci-failed-jobs.sh` — Plan defers UTF-8/multi-byte preservation for `sanitize_diagnostic_line` to manual macOS verification; T8 covers BEL/ESC only. Acceptable per plan scope, but CI will not catch a future `LC_ALL=C` regression on UTF-8 passthrough. **Suggested fix:** optional follow-up harness case with a UTF-8 fixture (e.g. `éè`) asserting byte preservation after `tr -d '[:cntrl:]'`.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_9: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: - **risk-integration** `scripts/ci-failed-jobs.sh:125-128` — TSV/KV job-name sanitization remains untested here (filed OOS_3 in plan). Pre-existing boundary, not introduced by this branch.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

