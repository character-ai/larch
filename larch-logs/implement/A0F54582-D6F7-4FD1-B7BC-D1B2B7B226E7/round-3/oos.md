### OOS_1: [OUT_OF_SCOPE] Branch noise, run logs, and non-2670 stack files
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: The diff against main includes bulk unrelated commits, committed run-log or keepalive artifacts, non-#2670 ship/dispatch changes, and general log churn. These items add review noise and process friction but are not treated as correctness defects in the plan-size scripts themselves for this scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

---

**Merge map (for traceability)**  
- FINDING_1 input + FINDING_11 input → **FINDING_1**  
- FINDING_2 input → **FINDING_2**  
- FINDING_3 input → **FINDING_3**  
- FINDING_4 input → **FINDING_4**  
- FINDING_5, 14, 16, 22 input → **FINDING_5**  
- FINDING_6, 20 input → **FINDING_6**  
- FINDING_7 input → **FINDING_7**  
- FINDING_9 input → **FINDING_8** (renumbered after in-scope 1–7)  
- FINDING_10 input → **FINDING_9**  
- FINDING_12 input → **FINDING_10**  
- FINDING_13 input → **FINDING_11**  
- FINDING_17 input → **FINDING_12**  
- FINDING_18 input → **FINDING_13**  
- FINDING_19 input → **FINDING_14**  
- FINDING_21 input → **FINDING_15**  
- FINDING_8, 15, 23, 24 input → **OOS_1**

**Note on numbering:** Sequential `### FINDING_1:` … `### FINDING_15:` are used for in-scope items in ascending order of the smallest source id per block; `### OOS_1:` follows (sources 8, 15, 23, 24). If your downstream validator requires `FINDING_8` through `FINDING_15` labels to match the original ids exactly, say so and the list can be re-titled without changing merged content.

**Why FINDING_22 merged into FINDING_5:** Same behavioral surface (documented argv / SECURITY wording vs actual Step 5d and `gh` behavior); severity **important** dominates **nit**. **Why FINDING_3 and FINDING_13 stay separate:** One is testability and best-effort semantics of the estimate; the other is repeated soft prompting without a latch—different failure modes and fixes.

Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

