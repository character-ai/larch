### [rejected] FINDING_1

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_1: Step 5c vs Gate C continuation banner punctuation mismatch
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Step 5c continuation banner punctuation differs from the Step 5 Gate C continuation banner in the same file. This is low impact (operator-facing visual consistency only, not behavior). Match Continue-banner punctuation to the existing Gate C pattern, or normalize both.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: Check (17) leaves key anti-halt / orchestrator-never prose unpinned in the Step 5b–5c window
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Check (17) does not pin ISSUES_* / sentinel / summary wording inside the Step 5b–5c window (structure reviewer), and does not pin **Why** / **How to apply** / **CI-backed** for orchestrator-never item 2 (testing reviewer). A shortened banner or deleted rationale could pass while weakening the regression signal the incident called for.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: Anti-halt parenthetical skips intermediate Step 5c sub-steps (5c.2–5c.5)
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Anti-halt parenthetical lists 5c.1→5c.6→5c.7 and omits 5c.2–5c.5. An orchestrator may still treat outputs after compose redact or plan-block-write as a natural stop because those sub-steps are not named in the enumerated chain, risking another summary-halt before publish/rename.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_4: Check (15b) redundant with check (17) for overlapping substring
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Check (15b) greps for 5c.7→6 on SKILL.md while check (17) already requires the full intra-Step-5 token that contains the same substring. That yields redundant CI signal: a future edit could satisfy (15b) with a stray 5c.7→6 mention outside the anti-halt line while breaking (17), or maintainers may think both checks guard distinct invariants.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_6: Post-edit shell checks not provable from diff-only review
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Plan acceptance requires three post-edit shell checks to pass; diff-only review cannot confirm `scripts/test-design-structure.sh`, `scripts/test-anti-improvised-wakeup.sh`, and `scripts/relevant-checks.sh` were run and succeeded on the final commit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

*(The source text also said to await or inspect CI, or attach command transcripts, showing those scripts pass before treating the plan as fully satisfied; that sentence lived only under **Concern**, not under **Suggested revision**, so it is not duplicated as a separate verbatim bullet.)*


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0

