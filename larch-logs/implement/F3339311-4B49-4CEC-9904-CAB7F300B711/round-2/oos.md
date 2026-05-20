### FINDING_1: [OUT_OF_SCOPE] **[correctness]** [`scripts/lib-vote-tally.md:19-30`](scripts/lib-vote-tally.md): Documents `accept_finding` thresholds and single-judge EXON behavior but not the multi-judge exoneration / tie logic in `classify_result`. **Suggested fix:** Add a short subsection describing the `neutral` vs `exonerated` branches (including `no > 0` dominance) so future edits do not treat the implementation plan’s simplified formula as the only spec.
- **Reviewer**: dyn-decision-table-output.txt
- **Concern**: - **[correctness]** [`scripts/lib-vote-tally.md:19-30`](scripts/lib-vote-tally.md): Documents `accept_finding` thresholds and single-judge EXON behavior but not the multi-judge exoneration / tie logic in `classify_result`. **Suggested fix:** Add a short subsection describing the `neutral` vs `exonerated` branches (including `no > 0` dominance) so future edits do not treat the implementation plan’s simplified formula as the only spec.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_2: [OUT_OF_SCOPE] **[correctness]** [`skills/shared/voting-protocol.md:176-185`](skills/shared/voting-protocol.md) and [`scripts/test-lib-vote-tally.sh:193-195`](scripts/test-lib-vote-tally.sh): Competition copy describes exoneration as “0 YES” with 1+ EXONERATE, while `classify_result` still maps `(1,0,1,eligible)` to `exonerated` (pre-existing; the diff only adds the same expectation for `eligible=2` at line 195). **Suggested fix:** Either narrow the code path for 1Y/0N/1E to match the prose (breaking change) or extend the protocol text to describe mixed YES/EXON/0NO outcomes and how they map to `exonerated` vs `neutral`.
- **Reviewer**: dyn-decision-table-output.txt
- **Concern**: - **[correctness]** [`skills/shared/voting-protocol.md:176-185`](skills/shared/voting-protocol.md) and [`scripts/test-lib-vote-tally.sh:193-195`](scripts/test-lib-vote-tally.sh): Competition copy describes exoneration as “0 YES” with 1+ EXONERATE, while `classify_result` still maps `(1,0,1,eligible)` to `exonerated` (pre-existing; the diff only adds the same expectation for `eligible=2` at line 195). **Suggested fix:** Either narrow the code path for 1Y/0N/1E to match the prose (breaking change) or extend the protocol text to describe mixed YES/EXON/0NO outcomes and how they map to `exonerated` vs `neutral`.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_3: [OUT_OF_SCOPE] architecture: scripts/lib-vote-tally.sh:79-90
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] accept_finding is YES-threshold-only; no/exonerate only affect downstream classify_result. Eligible vs parsed YES/NO/EXON/JUDGE_ERROR skew is a broader tally contract; unchanged by this diff. None for this PR; revisit only if tally inputs are validated.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=rejected

### FINDING_4: [OUT_OF_SCOPE] code-quality: scripts/lib-vote-tally.md:19-30
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Threshold docs omit multi-judge classify_result EXON vs NO tie rules. Pre-existing; file not in diff. Extend lib-vote-tally.md or skills/shared/voting-protocol.md when documenting policy.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### FINDING_5: [OUT_OF_SCOPE] code-quality: scripts/lib-vote-tally.md:28-31
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] lib-vote-tally.md does not document multi-judge EXON vs NO tie-break semantics for classify_result. Readers infer behavior only from code or tests; unchanged in this PR. Update the sibling markdown in a doc-focused change if you want the truth table co-located with the library contract.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### FINDING_6: [OUT_OF_SCOPE] risk-integration: (prompt implementation_plan vs scripts/lib-vote-tally.sh:132)
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Plan text omitted no==0 short-circuit; pure conjunction would regress 1Y/0N/1E to rejected. Misapplied plan could ship a subtle scoring regression. Align planning text with landed guard before reuse.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=rejected

### FINDING_7: [OUT_OF_SCOPE] risk-integration: scripts/lib-vote-tally.md (unchanged on branch)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Multi-judge classify_result EXON vs NO rules not documented in the API doc. Operators infer behavior from prose in voting-protocol or code only. Optional doc sync when editing classify_result again.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### FINDING_8: [OUT_OF_SCOPE] risk-integration: skills/review/scripts/test-tally-code-votes.sh (unchanged on branch)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] No 3-voter unanimous EXONERATE E2E fixture for in-scope findings. Lower regression signal if someone duplicated tally logic elsewhere; current bug is covered by classify_result unit tests. Optional: add a tally harness case when touching those tests.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_9: [OUT_OF_SCOPE] security: scripts/lib-vote-tally.sh:12-29
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] vote_for_id passes finding id into awk -v without regex-escaping id containing awk regex metacharacters could skew vote matching in theory. Not introduced by this diff; consider hardening in a dedicated change if ids are ever non-canonical.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

