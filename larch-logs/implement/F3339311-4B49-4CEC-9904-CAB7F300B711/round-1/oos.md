### FINDING_3: [OUT_OF_SCOPE] **[correctness]** [`scripts/lib-vote-tally.md:19-31`](scripts/lib-vote-tally.md:19-31) — The markdown contract documents `accept_finding` thresholds and single-judge `classify_result` behavior but does not spell out multi-judge exoneration tie-breaks; that gap predates this diff and makes it easier for future edits to drift from intended semantics without a spec to test against.
- **Reviewer**: dyn-voting-logic-output.txt
- **Concern**: - **[correctness]** [`scripts/lib-vote-tally.md:19-31`](scripts/lib-vote-tally.md:19-31) — The markdown contract documents `accept_finding` thresholds and single-judge `classify_result` behavior but does not spell out multi-judge exoneration tie-breaks; that gap predates this diff and makes it easier for future edits to drift from intended semantics without a spec to test against.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_4: [OUT_OF_SCOPE] **[correctness]** [`scripts/lib-vote-tally.sh:69-91`](scripts/lib-vote-tally.sh:69-91) — `accept_finding` ignores `exonerate` for acceptance (only `yes` vs `eligible`); [`scripts/test-lib-vote-tally.sh:49-50`](scripts/test-lib-vote-tally.sh:49-50) documents “1 voter, 1 EXONERATE → reject for implementation.” That asymmetry with `classify_result` is longstanding and not introduced by this branch.
- **Reviewer**: dyn-voting-logic-output.txt
- **Concern**: - **[correctness]** [`scripts/lib-vote-tally.sh:69-91`](scripts/lib-vote-tally.sh:69-91) — `accept_finding` ignores `exonerate` for acceptance (only `yes` vs `eligible`); [`scripts/test-lib-vote-tally.sh:49-50`](scripts/test-lib-vote-tally.sh:49-50) documents “1 voter, 1 EXONERATE → reject for implementation.” That asymmetry with `classify_result` is longstanding and not introduced by this branch.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=rejected

### FINDING_5: [OUT_OF_SCOPE] code-quality: scripts/lib-vote-tally.md
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Secondary classify_result tie rules for multi-judge EXON are not documented in the API markdown. Pre-existing documentation gap; not introduced by this diff. Optional follow-up: add a short classify_result precedence paragraph and keep in sync with skills/shared/voting-protocol.md.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### FINDING_6: [OUT_OF_SCOPE] correctness: scripts/lib-vote-tally.md (post-fix)
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] lib-vote-tally.md does not spell out multi-judge classify_result EXON tie rules. Humans maintainers rely on code or voting-protocol only. Add a concise classify_result multi-judge rule bullet when logic stabilizes.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### FINDING_7: [OUT_OF_SCOPE] risk-integration: skills/shared/voting-protocol.md:180-185
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Scoring prose for exonerated vs rejected omits how NO votes interact with EXONERATE. Operators may infer different outcomes than tally for split NO/EXON panels. Clarify in a follow-up doc edit whether NO votes can block exoneration when 0 YES and 1+ EXONERATE.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_8: [OUT_OF_SCOPE] risk-integration: skills/shared/voting-protocol.md:182-185
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Doc rows say exactly 1 YES for neutral; code uses YES/NO tie. Operator misreads scoreboard semantics vs tally; pre-existing doc drift. Update voting-protocol or classify comments in a separate change; not part of this diff.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

