### FINDING_1: [OUT_OF_SCOPE] **[correctness]** [`scripts/lib-vote-tally.md:19-30`](scripts/lib-vote-tally.md): Documents `accept_finding` thresholds and single-judge EXON behavior but not the multi-judge exoneration / tie logic in `classify_result`. **Suggested fix:** Add a short subsection describing the `neutral` vs `exonerated` branches (including `no > 0` dominance) so future edits do not treat the implementation plan’s simplified formula as the only spec.
- **Reviewer**: dyn-decision-table-output.txt
- **Concern**: - **[correctness]** [`scripts/lib-vote-tally.md:19-30`](scripts/lib-vote-tally.md): Documents `accept_finding` thresholds and single-judge EXON behavior but not the multi-judge exoneration / tie logic in `classify_result`. **Suggested fix:** Add a short subsection describing the `neutral` vs `exonerated` branches (including `no > 0` dominance) so future edits do not treat the implementation plan’s simplified formula as the only spec.
- **Suggested revision**: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] **[correctness]** [`skills/shared/voting-protocol.md:176-185`](skills/shared/voting-protocol.md) and [`scripts/test-lib-vote-tally.sh:193-195`](scripts/test-lib-vote-tally.sh): Competition copy describes exoneration as “0 YES” with 1+ EXONERATE, while `classify_result` still maps `(1,0,1,eligible)` to `exonerated` (pre-existing; the diff only adds the same expectation for `eligible=2` at line 195). **Suggested fix:** Either narrow the code path for 1Y/0N/1E to match the prose (breaking change) or extend the protocol text to describe mixed YES/EXON/0NO outcomes and how they map to `exonerated` vs `neutral`.
- **Reviewer**: dyn-decision-table-output.txt
- **Concern**: - **[correctness]** [`skills/shared/voting-protocol.md:176-185`](skills/shared/voting-protocol.md) and [`scripts/test-lib-vote-tally.sh:193-195`](scripts/test-lib-vote-tally.sh): Competition copy describes exoneration as “0 YES” with 1+ EXONERATE, while `classify_result` still maps `(1,0,1,eligible)` to `exonerated` (pre-existing; the diff only adds the same expectation for `eligible=2` at line 195). **Suggested fix:** Either narrow the code path for 1Y/0N/1E to match the prose (breaking change) or extend the protocol text to describe mixed YES/EXON/0NO outcomes and how they map to `exonerated` vs `neutral`.
- **Suggested revision**: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] architecture: scripts/lib-vote-tally.sh:79-90
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] accept_finding is YES-threshold-only; no/exonerate only affect downstream classify_result. Eligible vs parsed YES/NO/EXON/JUDGE_ERROR skew is a broader tally contract; unchanged by this diff. None for this PR; revisit only if tally inputs are validated.
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] code-quality: scripts/lib-vote-tally.md:19-30
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Threshold docs omit multi-judge classify_result EXON vs NO tie rules. Pre-existing; file not in diff. Extend lib-vote-tally.md or skills/shared/voting-protocol.md when documenting policy.
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] code-quality: scripts/lib-vote-tally.md:28-31
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] lib-vote-tally.md does not document multi-judge EXON vs NO tie-break semantics for classify_result. Readers infer behavior only from code or tests; unchanged in this PR. Update the sibling markdown in a doc-focused change if you want the truth table co-located with the library contract.
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] risk-integration: (prompt implementation_plan vs scripts/lib-vote-tally.sh:132)
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Plan text omitted no==0 short-circuit; pure conjunction would regress 1Y/0N/1E to rejected. Misapplied plan could ship a subtle scoring regression. Align planning text with landed guard before reuse.
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] risk-integration: scripts/lib-vote-tally.md (unchanged on branch)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Multi-judge classify_result EXON vs NO rules not documented in the API doc. Operators infer behavior from prose in voting-protocol or code only. Optional doc sync when editing classify_result again.
- **Suggested revision**: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] risk-integration: skills/review/scripts/test-tally-code-votes.sh (unchanged on branch)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] No 3-voter unanimous EXONERATE E2E fixture for in-scope findings. Lower regression signal if someone duplicated tally logic elsewhere; current bug is covered by classify_result unit tests. Optional: add a tally harness case when touching those tests.
- **Suggested revision**: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] security: scripts/lib-vote-tally.sh:12-29
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] vote_for_id passes finding id into awk -v without regex-escaping id containing awk regex metacharacters could skew vote matching in theory. Not introduced by this diff; consider hardening in a dedicated change if ids are ever non-canonical.
- **Suggested revision**: Address the concern above.

### FINDING_10: architecture: scripts/lib-vote-tally.sh:112-114
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] classify_result contract comment does not explain the compound EXON disjunct Operators auditing tie logic must reverse-engineer why no==0 is ORed with the inequality branch. Add a brief comment or md bullet documenting the two cases (legacy no==0 path vs exonerate>=no&&exonerate>yes).
- **Suggested revision**: Address the concern above.

### FINDING_11: code-quality: scripts/lib-vote-tally.sh:132
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Dense compound (( )) guard encodes multiple policies without an explanatory comment. Future edit may reintroduce a YES gate or change >= vs > for NO ties, regressing the fixed bug or altering ties silently. Add a one-line comment documenting the two cases (no==0 vs EXON beats NO when yes==0).
- **Suggested revision**: Address the concern above.

### FINDING_12: code-quality: scripts/lib-vote-tally.sh:132
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] The exoneration guard is a single dense arithmetic expression with nested logical operators. Reviewers must unpack parentheses to verify parity with tests; higher risk of accidental edits. Add a short comment naming the no==0 fast path vs the exonerate-majority path, or use two parallel elif branches for the same predicate shape.
- **Suggested revision**: Address the concern above.

### FINDING_13: code-quality: scripts/test-lib-vote-tally.sh:202
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Test description string is mildly imprecise vs the numeric relation being asserted. None; readability only. Reword label e.g. EXON beats NO for clarity.
- **Suggested revision**: Address the concern above.

### FINDING_14: correctness: scripts/lib-vote-tally.sh:128-133
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] New exoneration path for no>0 changes outcomes vs pre-change for some 0 YES tallies with NO and EXON votes. classify_result 0 1 1 3 (e.g. one JUDGE_ERROR among three effective voter files) was rejected before and is exonerated now; not covered by new tests (0Y/1N/2E and 0Y/2N/1E only). Add a test for 0Y/1N/1E (or tighten logic) if parity should not exonerate; otherwise document as intentional.
- **Suggested revision**: Address the concern above.

### FINDING_15: correctness: scripts/lib-vote-tally.sh:132
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Implementation plan's standalone formula `exonerate > 0 && exonerate >= no && exonerate > yes` omits the `no == 0 ||` disjunct present in the diff. classify_result 1 0 1 3 would become rejected (exonerate > yes is false), breaking the harness expectation at scripts/test-lib-vote-tally.sh:194 and existing 1Y/0N/multi-E log patterns. Update the plan or author docs to match the disjunctive predicate; do not drop the no==0 arm when refactoring.
- **Suggested revision**: Address the concern above.

### FINDING_16: correctness: scripts/lib-vote-tally.sh:132
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Implemented exoneration guard does not match the implementation plan’s stated formula; code adds `(no == 0 || …)` instead of only `exonerate >= no && exonerate > yes`. Applying the plan text literally would classify e.g. classify_result 1 0 1 3 and 2 0 1 3 as rejected (exonerate > yes false) after accept_finding fails, regressing prior yes>0 && exonerate>0 && no==0 semantics and failing existing exoneration tests. Update the plan / ticket prose to document the actual predicate and the need for the no==0 disjunct to preserve legacy YES+EXON zero-NO exoneration when exonerate does not exceed yes.
- **Suggested revision**: Address the concern above.

### FINDING_17: correctness: scripts/lib-vote-tally.sh:132
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] classify_result exoneration branch widened vs pre-change yes>0&&no==0 guard Mixed panels such as 0Y/1N/1E/3 elig (and similarly 1Y/2N/2E/3 elig) now map to exonerated where the old branch required no==0 and yes>0 so they previously mapped to rejected. Downstream tally consumers may drop more findings from actionable workflows. Confirm intended policy; if only unanimous EXON (zero NO) should exonerate narrow the predicate and add tests; if broader rule is intended document it in scripts/lib-vote-tally.md and skills/shared/voting-protocol.md.
- **Suggested revision**: Address the concern above.

### FINDING_18: correctness: scripts/lib-vote-tally.sh:132
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Implementation-plan formula omits the no==0 disjunct present in the shipped elif. Following the plan verbatim (exonerate >= no && exonerate > yes only) yields rejected for classify_result 1 0 1 3 (1Y/0N/1E full panel) because exonerate > yes is false, regressing legacy exonerated behavior. Document that the shipped condition is no==0 || (exonerate >= no && exonerate > yes); do not collapse to the plan-only AND form.
- **Suggested revision**: Address the concern above.

### FINDING_19: correctness: scripts/lib-vote-tally.sh:132-133
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Exoneration branch applies EXON plurality when NO>0 (exonerate>=no && exonerate>yes), not only unanimous EXON with zero NO. 0Y/1N/1E on a 3-eligible panel flips from rejected (old yes>0 guard) to exonerated; scoreboard and PR-facing tallies change for that vote shape. Lock with tests (e.g. classify_result 0 1 1 3) and document tie-break in scripts/lib-vote-tally.md alongside classify_result.
- **Suggested revision**: Address the concern above.

### FINDING_20: correctness: scripts/test-lib-vote-tally.sh:72-81
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Tests added beyond the single case enumerated in the plan (0 0 3 3). No functional breakage; only plan-to-diff checklist mismatch for strict traceability. Optional: extend the plan’s test bullet list to include the extra cases for 1:1 traceability.
- **Suggested revision**: Address the concern above.

### FINDING_21: risk-integration: scripts/lib-vote-tally.sh:132
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Exoneration guard uses (no==0||(exonerate>=no&&exonerate>yes)) rather than the plan snippet alone; no comment explains the disjunct. A refactor to the plan text only would classify e.g. 1Y/0N/1E on a 3-judge panel as rejected instead of exonerated. Add a brief comment above the elif documenting why no==0 bypasses exonerate>yes.
- **Suggested revision**: Address the concern above.

### FINDING_22: risk-integration: scripts/test-lib-vote-tally.sh
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Harness omits explicit 0Y/1N/1E eligible-3 case though behavior changed vs pre-diff classifier for that shape. Tie at 0 YES with equal EXON and NO is not regression-locked. Add assert for classify_result 0 1 1 3 → exonerated if intended.
- **Suggested revision**: Address the concern above.

