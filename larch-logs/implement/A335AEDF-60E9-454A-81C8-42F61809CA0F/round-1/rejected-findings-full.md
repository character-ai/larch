### [rejected] FINDING_10

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_10: correctness: skills/review/scripts/aggregate-findings.sh:738-769
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Post-dispatch case statement has no default branch when MERGE_PIPELINE_RC is unset. Future _agg_pipeline_for_candidate edit could exit without emit_result stdout keys. Add default *) arm mapping to validation-failed with emit_result exit 0.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_15: risk-integration: skills/review/scripts/test-aggregate-findings.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Missing optional three-phase test when Codex absent and Cursor narration-only. Phase-3 Claude fallback after double pattern miss is untested in CI. Add codex-absent + cursor-narration + claude-valid integration case asserting PHASE3_SLOTS and ALL_OUTPUT_TOOLS=claude.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: code-quality: skills/review/scripts/aggregate-findings.sh:751
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] RC=1 warning text always says empty merge Preamble narrow-trigger failures log misleading execution-issues text Rename warning to narrow-trigger validator rejection or branch on stderr token
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_23

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_23: architecture: skills/review/scripts/aggregate-findings.sh:687-768
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] No harness for all-phase narration/pattern miss → dispatch-failed. When every tool returns plan-mode narration, review-core continues with stale findings instead of aggregator-validation-exhausted stall. Add all-phase narration stub test; document dispatch-failed as intentional non-stall in aggregate-findings.md.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_26

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_26: correctness: CHANGELOG.md:12
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] CHANGELOG bullet is vaguer than the plan draft about which consumer files changed. Harder to audit #2881 doc surface from release notes alone. Name review-core.md, review-and-fix.sh breadcrumb, and test-review-core.sh stub explicitly in the bullet.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: code-quality: skills/review/scripts/aggregate-findings.sh:687
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Pattern ERE duplicated across script docs SECURITY CHANGELOG and tests One-sided edit could leave dispatcher gate and docs/tests inconsistent Centralize pattern in one shell variable at top of aggregate-findings.sh
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: code-quality: skills/review/scripts/test-aggregate-findings.sh:337-374
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] write_external_tool_stubs duplicates test-dispatch-with-waterfall stubs Stub behavior drift between harnesses causes false confidence Extract shared test stub helper or cross-reference single canonical stub file
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: code-quality: skills/review/scripts/aggregate-findings.md:26
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Behavior contract crammed into one giant bullet Harder to keep SECURITY.md and aggregate-findings.md in sync Split into shorter bullets by concern
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

