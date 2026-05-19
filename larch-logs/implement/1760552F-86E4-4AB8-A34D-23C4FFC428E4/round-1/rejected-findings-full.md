### [rejected] FINDING_15

### FINDING_15: code-quality: scripts/dispatch-code-voters.sh:138-203 scripts/lib-vote-tally.sh:12-38
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Duplicated vote_for_id awk remains after rename. Future edits to vote matching can drift between lib and dispatch copy. Optional refactor to reuse vote_for_id from sourced lib when practical.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_16

### FINDING_16: code-quality: scripts/lib-vote-tally.md:276-281
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Threshold bullet names JUDGE_ERROR as if accept_finding accepts that token; API is aggregate yes/no/exo counts only. Integrators may think accept_finding has a JUDGE_ERROR parameter. Clarify wording to tie JUDGE_ERROR to vote_for_id / tally counting, not accept_finding arguments.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 NEUTRAL=0

### [rejected] FINDING_23

### FINDING_23: risk-integration: scripts/test-lib-vote-tally.sh:54-56
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] accept_finding case descriptions say JUDGE_ERROR but only yes/no/exo/eligible integers are passed Future edits may wrongly assume accept_finding consumes JUDGE_ERROR or parser-fallback counts Rename descriptions to reflect insufficient YES / abstract non-accepting slots or tie text to vote_for_id-driven scenarios only
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 NEUTRAL=0

### [rejected] FINDING_24

### FINDING_24: risk-integration: scripts/test-lib-vote-tally.sh:82-87
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Regression comment says zero FINDING_N: lines while fixture is prose-only (no vote lines at all) Mild mismatch between test name and literal file shape Optional tighten fixture to include non-parseable heading lines if literal alignment matters
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 NEUTRAL=0

### [rejected] FINDING_30

### FINDING_30: risk-integration: skills/review/scripts/tally-code-votes.sh (output contract) / consumer automation
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Per-finding output renames Vote tally field NEUTRAL= to JUDGE_ERROR= and table column NEUT to JERR. External golden tests or grep-based tooling keyed on NEUTRAL= or NEUT headers fail after upgrade. Document migration for out-of-repo consumers; finish first-party doc updates (tally-code-votes.md).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

