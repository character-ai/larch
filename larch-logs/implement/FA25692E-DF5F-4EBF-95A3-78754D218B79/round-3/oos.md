### FINDING_10: [OUT_OF_SCOPE] architecture: scripts/launch-review.sh:510
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] run-external progress lines append to events.jsonl Bloat or rare parse confusion if progress text ever looks like JSON Out of scope; optional tee filter later
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### FINDING_11: risk-integration: scripts/test-render-run-summary-callsites.sh:11-19
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Callsite harnesses grep only --claude-input-tokens, not Codex per-bucket flags in render-final-summary.sh / write-final-report.sh. A refactor removes --codex-input-tokens/--codex-cached-input-tokens forwarding; launchers still record buckets but final-summary cost lines hit render-cost-line aggregate fallback and BLENDED_WARN returns. Require --codex-input-tokens and --codex-cached-input-tokens in callsite tests, or add fixture-driven final-summary cost test with non-zero BUCKETS_codex and assert no blended-rate stderr.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_14: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **security** `scripts/lib-quiet.sh:176-181` (pre-existing) — EXIT-trap chaining uses `eval` on a captured trap body. Not introduced or amplified by this branch’s Codex work; noted only because `lib-quiet.sh` is touched for breadcrumb streaming. **Suggested fix:** (follow-up) replace `eval` with a direct trap restore pattern if trap injection ever becomes a concern.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_15: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 2. **risk-integration** `scripts/launch-review.sh` / `scripts/launch-codex-implement.sh` / `scripts/launch-codex-ci.sh` (documented contract) — Auth/transient classification is stderr-only after splitting Codex stdout to the events sidecar. This is intentional and tested; a future Codex CLI regression that routes auth/quota text only on stdout would weaken retry classification without exposing credentials. **Suggested fix:** monitor via launcher tests; tee non-JSON stdout lines into the sidecar only if Codex behavior changes (plan follow-up).
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### FINDING_19: [OUT_OF_SCOPE] risk-integration: skills/review-and-fix/scripts/review-and-fix.sh:256-257
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Other Codex call sites still use combined 2>&1 and no JSONL usage capture. /review-and-fix or lint-fix Codex runs may still miss per-bucket telemetry or trigger BLENDED_WARN outside the three fixed launchers. Follow-up: apply the same --json events sidecar + parse-codex-usage.sh pattern to those invokers.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_20: [OUT_OF_SCOPE] code-quality: scripts/launch-codex-ci.sh:254
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] launch-codex-ci.sh always exits 0 while exposing failure via LAUNCHER_EXIT KV. Callers checking only shell exit may treat failed Codex CI as success; unrelated to bucket capture but affects failure recovery. Pre-existing; consider aligning exit code with LAUNCHER_EXIT in a separate change.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### FINDING_5: [OUT_OF_SCOPE] code-quality: (branch)
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Branch mixes #2813 Codex token capture with breadcrumb lib-larch-log rollout and larch-logs flush in one PR. Reviewers and bisect blame conflate unrelated regressions; revert of one feature risks reverting the other. Split into focused PRs when feasible.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_6: [OUT_OF_SCOPE] code-quality: scripts/parse-codex-usage.sh:47-49
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] jq failures are reported as no usage events. Operator sees no usage events for a corrupt JSONL file when jq actually crashed or hit a parse error. Distinguish jq exit/status from zero-usage fail-closed in stderr diagnostics.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected

