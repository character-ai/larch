# Review Round 4

- Mode: `diff`
- 7 accepted, 4 rejected (3 exonerated)

## Accepted Findings

### FINDING_1: Shared tier fallback parsing can diverge or misclassify reports
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Tier resolution is duplicated and partly grep-based across timing/reporting scripts, which can diverge from the canonical workflow_path-first classification behavior or misread crafted/conflicting JSON when stricter parsers are unavailable.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_10: SIMPLE reviewer guidance can suppress security hardening
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: SIMPLE tier prose emphasizes exonerating non-correctness findings, so security hardening that is not framed as correctness may be voted down.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


### FINDING_13: Collaborative sketches docs still reference deleted Quick mode
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `docs/collaborative-sketches.md` still documents Quick mode sketch attribution, implying a deleted 2-slot Cursor/Codex sketch path still exists beside SIMPLE/HARD.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_2: Duplicate Focus area enum anchors add noise
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Ten repeated Focus area enum anchor comments in `skills/design/SKILL.md` look accidental and may mislead readers or grep-based references.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_3: Topology vocabulary still uses legacy round-cap wording
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `skills/shared/topology.tsv` still describes Step 5 round-cap terminology instead of the updated design classification or tier-label vocabulary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_5: Step 3 cap counter is not persisted at review entry
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The Step 3 review-round counter is persisted only after panel settlement, so empty or unrecognized statuses, crashes after launch, or plan-contract expectations can leave the count stale and allow extra panels beyond the tier cap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_8: Step 3 cap harness lacks HARD-tier coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The cap test only covers SIMPLE cap=3, so regressions around HARD cap=5 blocking or allowing the fifth round could pass CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


