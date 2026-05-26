### OOS_1:
- **Description**: Consumer doc still lists per-outer aggregator output paths. Scenario: After collapse, only `aggregator-output.txt` plus phase-suffixed dispatcher paths remain; `aggregator-output-codex.txt` / `aggregator-output-claude.txt` are removed from the script.
- **Reviewer**: Cursor-Edge
- **Severity**: nit
- **Focus area**: architecture
- **Location**: skills/review/scripts/review-core.md:63
- **Phase**: design


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

### OOS_2:
- **Description**: Harness doc still describes outer-waterfall coverage. Scenario: `test-aggregate-findings.md` references progression coverage implicitly via empty-merge cases tied to removed outer waterfall semantics.
- **Reviewer**: Cursor-Edge
- **Severity**: nit
- **Focus area**: risk-integration
- **Location**: skills/review/scripts/test-aggregate-findings.md:11-19
- **Phase**: design


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=1 Result=exonerated

