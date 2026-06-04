### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: All-already-filed design wording can hide other OOS sources
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `oos-pipeline.md` wording for all-already-filed design batches can be read as skipping combine/file steps even when review or main-agent OOS remains unfiled.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_17: Load-directive checks are too global
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Structure tests only check a global load-directive count, not bounded adjacency to each required entry point, so all directives could cluster in one section while another entry loses its mandatory pointer.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_18: Materialize helper contract header is not covered
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `materialize-manifest-oos.md` is not covered by the existing reference-header triplet scan, allowing header drift without CI failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_24

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_24: Manifest titles are used as printf format strings
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: User-controlled manifest titles can contain `%` format conversions that corrupt headings or abort materialization under `set -e`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: Python materialize hook uses hardcoded repo-relative script path
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `python/ship.py` resolves `materialize-manifest-oos.sh` using a hardcoded repo-relative path rather than `CLAUDE_PLUGIN_ROOT` with fallback, which can break non-standard plugin layouts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_40

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_40: Run-statistics accepted count is not scoped to newly filed issues
- **Reviewer(s)**: dyn-evidence-logging-output.txt
- **Severity**: latent
- **Concern**: `SKILL.md` defines the accepted OOS statistic without excluding sentinel-recovered or already-filed items, risking inflated `run-statistics.md` counts on reruns.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-evidence-logging-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_41

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_41: OOS pipeline does not explicitly collect rejected review OOS into NDJSON
- **Reviewer(s)**: dyn-evidence-logging-output.txt
- **Severity**: important
- **Concern**: Step 6 says rejected/non-accepted entries remain under a rejected sub-block, but lacks an executable collection step to append those markers to checkpoint-visible NDJSON, which can make the disposition gate fail after accepted URL rows are written.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-evidence-logging-output.txt: Address the concern above.

Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: Step 2 parses manifest observation count twice
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `step2-implement.sh` computes `oos_observations` length separately from the materialization helper, duplicating JSON parsing on the complete path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: Structure test over-pins documentation wording
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `scripts/test-implement-structure.sh` contains a large brittle substring block duplicating `oos-pipeline.md`, so harmless documentation wording edits can break CI without behavior changing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

