### [rejected] FINDING_1

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_1: architecture: branch bundles design scope with ship-driver default flip
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: The branch bundles #3548 design scope-anchoring (~80 files) with the ship-driver default flip. A regression or review finding on design scripts can block or confuse ship-flip approval; bisect cannot isolate ship-only behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Split PRs or isolate ship-only commits for final review.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_14: correctness: no test that routine _write_ship_state preserves seeded RESUME_PHASE/CALLER_KIND
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: A regression that blanks resume tokens during routine phase writes would break `ship_pr_pre_push` handoff re-entry without CI catching it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add test pre-seeding resume keys then routine phase write.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: correctness: SKILL Step 8+ exit-matrix preamble not bash/Python scoped
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: With Python as the default Step 8+ driver, the orchestrator may parse `ship-pr-state.sh` and apply the bash exit-code matrix even when the active driver emits JSON-first semantics. The preamble does not clearly scope bash vs Python routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Reword to bash-first / Python-JSON-first explicitly.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_8: risk-integration: Exit 6 fourth-failure stall persistence is prose-only
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: After the fourth transient retry (exit 6), stall metadata persistence is described only in `skills/implement/SKILL.md` prose. Without a mechanical helper or test pin, the orchestrator can omit stall key rewrites and leave `ship-pr-state.sh` inconsistent with the documented stall contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add helper or mechanical test pin for Exit 6 stall persistence.
  - From cursor-specialist-edge-cases-output.txt: Mechanize via helper script or accept with stronger integration test.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

