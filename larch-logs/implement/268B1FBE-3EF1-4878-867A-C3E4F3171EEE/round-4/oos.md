### FINDING_4: **Important** `risk-integration` `scripts/render-specialist-prompt.sh:323` / `skills/review/scripts/collect-findings.sh:392` — The new reviewer grammar requires OOS bullets to use plain backtick file refs, but the collector only preserves file refs in markdown-link form like ``[`path`]``. A compliant OOS bullet such as `- **risk-integration** \`scripts/foo.sh:12\` — ...` is normalized to `[OUT_OF_SCOPE] risk-integration`, dropping the path needed by downstream issue serialization and conflict detection. **Suggested fix:** update the collector to extract the first plain backtick file token too, and add a regression using the exact rendered prompt grammar.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `risk-integration` `scripts/render-specialist-prompt.sh:323` / `skills/review/scripts/collect-findings.sh:392` — The new reviewer grammar requires OOS bullets to use plain backtick file refs, but the collector only preserves file refs in markdown-link form like ``[`path`]``. A compliant OOS bullet such as `- **risk-integration** \`scripts/foo.sh:12\` — ...` is normalized to `[OUT_OF_SCOPE] risk-integration`, dropping the path needed by downstream issue serialization and conflict detection. **Suggested fix:** update the collector to extract the first plain backtick file token too, and add a regression using the exact rendered prompt grammar.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

