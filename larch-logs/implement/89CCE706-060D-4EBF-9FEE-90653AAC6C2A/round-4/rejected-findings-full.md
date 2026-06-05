### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: Duplicate static slot IDs across Cursor and Codex
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `skills/review/scripts/dispatch-panel.sh` (≈97) reuses the same manifest `slot` slug for Cursor and Codex static peers (`security`, etc.), unlike design review’s vendor-prefixed slots. Drop accounting still disambiguates via `tool`, but slot-keyed diagnostics and cross-skill manifest comparison are ambiguous.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Mirror design-style distinct slot names if safe for tally


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: Duplicated `normalize_reviewer_output_base` risks threshold/coverage desync
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `normalize_reviewer_output_base` is duplicated in `review-core.sh` and `check-reviewer-failure-threshold.sh` (≈594–610). Suffix-handling changes can desync threshold math from the coverage gate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract shared lib and source both scripts from it.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: Dead structure/plan-fidelity mappings in vote tally
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `skills/review/scripts/tally-code-votes.sh` (≈288–293) retains dead structure and plan-fidelity focus mappings after archetype collapse, adding confusing maintenance surface before conditional spawning work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Remove dead case arms or document legacy-only attribution.

---


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

