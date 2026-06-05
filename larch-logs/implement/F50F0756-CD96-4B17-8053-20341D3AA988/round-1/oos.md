### FINDING_12: [OUT_OF_SCOPE] correctness
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: 1. **correctness** `skills/implement/scripts/test-write-final-report.sh:530-533` — The new case asserts substring presence (banner, marker, lines bullet, PR bullet) but not `<!-- larch:run-summary v=1 -->` or `assert_schema_ordered`, unlike the preceding `impl_bl` stage2 block (`477-493`). **Suggested fix:** If bullet-order regressions in merged-outcome fallback matter, mirror the stage2 schema-order assertions with the bucketed-lines expected sequence; otherwise this is acceptable minimal coverage per the plan.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_13: [OUT_OF_SCOPE] architecture
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: 2. **architecture** `skills/implement/scripts/write-final-report.sh:119` — `compute-pr-line-counts.sh` is invoked with no explicit timeout; a hung `gh api` would stall `write-final-report.sh` before any fallback path. **Why out of scope:** pre-existing production limitation, explicitly accepted as document-only in the issue plan; this branch does not touch that code.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_14: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: 3. **risk-integration** `skills/implement/scripts/test-write-final-report.sh:528-529` — Helper stderr is redirected to `/dev/null`, so diagnostics from `compute-pr-line-counts` or render-failure logging are invisible when assertions fail. **Why out of scope:** same suppression pattern as neighboring fallback tests (`472-473`, `555-556`); not introduced by this diff.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### FINDING_5: [OUT_OF_SCOPE] risk-integration: skills/implement/scripts/test-write-final-report.sh:555-557
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] fork_fb reaches stage2 fallback with LINES_DATA_OK likely true but never asserts bucketed Lines bullet Forked-dry-run fallback may emit bucketed line counts alongside fork notes without any assertion catching format regressions on that combined path Optionally extend fork_fb with the same Lines and PR assert_contains calls (not required for this PR plan)
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_8: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **security** `skills/implement/scripts/write-final-report.sh:521-526` — `compose_self_fallback` emits `PR_URL` and `ISSUE_URL` from `ship-pr-state.sh` / session files into markdown via `printf --` without URL allowlisting or markdown escaping; the new test now pins that PR bullet shape (`- **PR**: #43 — https://example.test/pr/43`). **Suggested fix:** If GitHub comment injection from poisoned session state is a concern, apply outbound sanitization (e.g. `redact-secrets.sh` plus URL scheme/host allowlist) to `summary-final.md` before `tracking-issue-summary.sh` upsert — pre-existing behavior, not introduced by this branch.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_9: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 2. **security** `scripts/compute-pr-line-counts.sh:58` — `gh api --paginate` has no explicit timeout; a hung network call could stall `write-final-report.sh`. **Suggested fix:** Documented accepted limitation per the issue plan; optional hardening would be a separate change — not in this diff.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

