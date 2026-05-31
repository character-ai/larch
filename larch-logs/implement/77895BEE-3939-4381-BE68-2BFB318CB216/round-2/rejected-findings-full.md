### [rejected] FINDING_1

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_1: test-degraded-tools-gate.sh Cases 13–16 duplicate primary matrix coverage
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Cases 13–16 duplicate argv and assertions already added to Cases 2–4 and 3/7. Future edits to explanation text may require updating four cases instead of one, with no extra branch coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Merge text assertions into the primary matrix cases; keep at most Case 14 for design both-down if Case 4 stays review-only.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: BOTH_DOWN=false auto-proceed allows env fallback when argv probe flags omitted
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Auto-proceed on BOTH_DOWN=false still allows env fallback when argv flags are omitted. Stale CURSOR_PRESENT=true in shell + Codex probe-failed with partial flags → BOTH_DOWN=false → interactive run auto-proceeds without AskUserQuestion; pre-change behavior prompted on any DEGRADED=true.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Require all four probe flags on argv before BOTH_DOWN=false can authorize auto-proceed; treat any omission as prompt path.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: interactive gate branching lacks shell mechanical enforcement
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Interactive gate branching is LLM-orchestrated only; no shell enforces exact BOTH_DOWN parse or sentinel write. Misparsed or empty BOTH_DOWN with loose inequality could auto-proceed when both tools are down, or re-show gate on resume if sentinel omitted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Add a mechanical interactive gate helper script with exact-string BOTH_DOWN handling and sentinel management.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: sentinel prevents re-prompt but procedure lacks skip-if-exists gate entry guard
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Sentinel prevents re-prompt but procedure lacks skip-if-exists entry guard. Orchestrator always runs degraded-tools-gate.sh on Step 0 re-entry; sentinel only prevents re-AskUserQuestion so auto-proceed path can re-print full explanation on implement resume-plan-tail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add normative if-sentinel-exists skip entire gate block; mirror in four SKILL.md gate bullets


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: duplicated BOTH_DOWN closing if/else in degraded-tools-gate.sh
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Duplicated BOTH_DOWN closing if/else in design and non-design branches. One branch could get the auto-proceed line updated and the other left stale.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Factor shared auto-proceed emit; keep only skill-specific Continue strings in the BOTH_DOWN=true branch.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: no mechanical CI check for BOTH_DOWN fail-safe parse path
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Fail-safe parse path (empty/unset BOTH_DOWN → prompt) has no mechanical CI check. An orchestrator edit could use [[ "$BOTH_DOWN" != "true" ]] or drop BOTH_DOWN parsing; degraded single-tool runs would auto-proceed without AskUserQuestion and CI would stay green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add grep/structure contract on SKILL.md + external-reviewers.md for exact-string BOTH_DOWN == false check


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_8: both-down matrix lacks binary-missing (or mixed-mode) BOTH_DOWN=true coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Both-down matrix only covers dual probe-failed. Misclassification for dual binary-missing would not be caught by current BOTH_DOWN=true assertions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add one both-binary-missing (or mixed-mode) BOTH_DOWN=true case with explanation closing-line pins


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

