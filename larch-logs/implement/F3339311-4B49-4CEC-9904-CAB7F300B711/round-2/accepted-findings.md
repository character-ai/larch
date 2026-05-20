### FINDING_10: architecture: scripts/lib-vote-tally.sh:112-114
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] classify_result contract comment does not explain the compound EXON disjunct Operators auditing tie logic must reverse-engineer why no==0 is ORed with the inequality branch. Add a brief comment or md bullet documenting the two cases (legacy no==0 path vs exonerate>=no&&exonerate>yes).
- **Suggested revision**: Address the concern above.


### FINDING_14: correctness: scripts/lib-vote-tally.sh:128-133
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] New exoneration path for no>0 changes outcomes vs pre-change for some 0 YES tallies with NO and EXON votes. classify_result 0 1 1 3 (e.g. one JUDGE_ERROR among three effective voter files) was rejected before and is exonerated now; not covered by new tests (0Y/1N/2E and 0Y/2N/1E only). Add a test for 0Y/1N/1E (or tighten logic) if parity should not exonerate; otherwise document as intentional.
- **Suggested revision**: Address the concern above.


### FINDING_15: correctness: scripts/lib-vote-tally.sh:132
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Implementation plan's standalone formula `exonerate > 0 && exonerate >= no && exonerate > yes` omits the `no == 0 ||` disjunct present in the diff. classify_result 1 0 1 3 would become rejected (exonerate > yes is false), breaking the harness expectation at scripts/test-lib-vote-tally.sh:194 and existing 1Y/0N/multi-E log patterns. Update the plan or author docs to match the disjunctive predicate; do not drop the no==0 arm when refactoring.
- **Suggested revision**: Address the concern above.


### FINDING_17: correctness: scripts/lib-vote-tally.sh:132
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] classify_result exoneration branch widened vs pre-change yes>0&&no==0 guard Mixed panels such as 0Y/1N/1E/3 elig (and similarly 1Y/2N/2E/3 elig) now map to exonerated where the old branch required no==0 and yes>0 so they previously mapped to rejected. Downstream tally consumers may drop more findings from actionable workflows. Confirm intended policy; if only unanimous EXON (zero NO) should exonerate narrow the predicate and add tests; if broader rule is intended document it in scripts/lib-vote-tally.md and skills/shared/voting-protocol.md.
- **Suggested revision**: Address the concern above.


