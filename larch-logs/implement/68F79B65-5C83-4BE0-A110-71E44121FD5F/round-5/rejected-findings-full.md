### [rejected] FINDING_10

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_10: risk-integration: skills/design/scripts/test-findings-classification.sh:201-211
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Parser harness only tests quiet capture via LARCH_QUIET_DISABLE=1, not default larch_quiet_init FD 3 path used by tally. Awk/emit_kv boundary break under quiet mode would not fail CI. Add parser case capturing FD 3 with quiet enabled (no LARCH_QUIET_DISABLE).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: risk-integration: skills/design/scripts/tally-plan-review.sh:345-347
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] MainAgent adjudication can accept findings in markdown while TSV voting_result stays rejected with empty vN columns. Downstream analytics treating TSV voting_result as authoritative would mis-score MainAgent rounds. Document in harness or add consumer-oriented assertion comment.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: risk-integration: scripts/test-render-voter-prompt.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Harness checks axis enum templates but not lowercase literal examples in rendered prompt lines. Uppercase examples could reach judges and fail parse-rate until manual discovery. grep -Fq CORRECTNESS=true (and peers) on both grammar renders.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_18: correctness: skills/design/scripts/tally-plan-review.sh:345-347
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] MainAgent TSV rows force voting_result=rejected while MainAgent vote_for_id can accept findings in markdown artifacts. Analytics on TSV voting_result undercount accepts when 0-judge MainAgent adjudication accepted items. Document contract or use distinct voting_result for MainAgent-only TSV rows.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_19: correctness: scripts/parse-judge-vote-and-rating.sh:50-68
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Glued YES-CORRECTNESS= tokens parse vote via lib-vote-tally but not separate CORRECTNESS= axis. Judge omits space after YES; forensic row shows empty correctness and uncertain=true despite substantive vote. Document whitespace requirement in voter prompts or strip vote token before axis split in awk.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_22

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_22: correctness: skills/design/scripts/test-tally-plan-review.sh:1-312
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Planned test-tally-plan-review extensions largely absent Plan-required mutex, deprecation stderr, sanitization, and explicit-out tests not in this harness Port missing cases from plan section or update acceptance to single harness
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_23

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_23: architecture: skills/design/scripts/plan-review-loop.sh:100-102
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Header-only TSV uses inline helper not tally invocation Diverges from plan preferred empty-ballot tally as header authority Invoke tally-plan-review.sh with empty ballot for header-only paths
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: code-quality: skills/design/scripts/tally-plan-review.sh:116-248
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Three overlapping slot-placement helpers for legacy vs explicit --voter. Future slot-rule changes must be edited in multiple places; easy to re-break waterfall or middle-slot semantics. Collapse to one assign_voter_at_position after slot-index fix.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: code-quality: skills/design/scripts/tally-plan-review.sh:326-360
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Redundant vote_for_id and parser subprocesses per TSV cell. Large ballots multiply shell/awk work without functional benefit. Cache tally_votes_for_id outputs and reuse for TSV columns.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: code-quality: scripts/parse-judge-vote-and-rating.sh:83-87
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Four awk invocations to split one parser TSV line. Small per-call overhead; unnecessary complexity vs IFS read. Split the tab line once in Bash after awk.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_6: code-quality: skills/design/scripts/tally-plan-review.sh:79-81
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Contract violation exits use 2; plan says 1. Callers grepping exit 1 only may mis-handle mutex errors. Align exit code with plan or document 2 in tally-plan-review.md.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

