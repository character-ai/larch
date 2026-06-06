### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: Drift-fence prose duplicated across normative references
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `_postplan_rc=14` drift handling is duplicated across `SKILL.md`, `approval-gates.md`, and `discussion-rounds.md`. One reference updated without the others causes operator prompts to diverge across Step 2b Gate B and discussion re-emit paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Centralize drift-fence prose in one reference; link from SKILL and discussion-rounds.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: plan-review-loop.sh legacy multi-round naming
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Script name and `--round-cap` argv imply multi-round loop though behavior is single-pass. Maintainers may reintroduce inner-loop logic or misconfigure `round-cap` expecting convergence behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Rename or document legacy naming; deprecate mandatory `--round-cap` when safe.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: round-num exceeding round-cap now exits 0 silently
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `--round-num` exceeding `--round-cap` now exits 0 because round-cap is inert (`test-plan-review-loop.sh:9935-9938`). External scripts passing `round-num > round-cap` would silently proceed instead of failing fast.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Document breaking change and optionally emit a stderr warning when round-num exceeds round-cap.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_15: Round snapshot failure only emits WARN on terminal exit
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Round snapshot failure on terminal exit only emits WARN; `LOOP_STATUS` unchanged (`plan-review-loop.sh:463-475`). tally-error/panel-failed runs may reach Gate C with incomplete `plan-review/round-N` forensic artifacts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Elevate snapshot failure to panel-failed or block downstream Gate C when round artifacts are mandatory.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_17: drift_exceeds uses strict greater-than boundary
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `drift_exceeds` uses strict greater-than (`current > baseline * multiple`; `check-plan-size.sh:172-178`). With default multiple 2, a plan exactly doubled in lines (ratio 2.0) does not trigger drift; operators expecting ">= 2x" get silent pass-through.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Document strict boundary in flags.md/prompts or change comparison to >= if inclusive 2x is intended.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_19: Dual ratio computation paths in check-plan-size.sh
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `ratio_token` uses python3/awk/integer fallbacks for display-only ratios while `drift_exceeds` uses separate integer math (`check-plan-size.sh:132-170`). Unnecessary complexity and two ratio representations that can disagree at display boundaries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Simplify to one ratio computation path (prefer awk or integer) shared with drift_exceeds.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

