### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: `manual_gate_b` jq read does not coerce non-boolean JSON
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `jq -r '.manual_gate_b // false'` can return non-boolean strings or other corrupt values, routing unpredictably between auto and manual Gate B branches.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: Gate B auto-apply trust boundary may allow untrusted reviewer prose to affect validation probes
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Default Gate B auto-apply can merge accepted reviewer findings into `plan.txt` without per-finding consent and then run `EMIT_PLAN` plus full-budget `VALIDATE_PLAN_COMMANDS`. Compromised or mistaken reviewer prose can therefore indirectly influence allowlisted dry-run probes before Gate C.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: Plan acceptance blocked-by edge is not verifiable from branch diff
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Acceptance lists native GitHub blocked-by edge `#2667 blocked-by #2930`, but that relationship is not verifiable from the branch diff. Dependent work may proceed before #2930 lands.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_22

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_22: Same-shell re-source can leave stale `MANUAL_REQUESTED=true`
- **Reviewer(s)**: dyn-session-env-manual-propagation-output.txt
- **Severity**: latent
- **Concern**: `write-design-current-env.sh` omits `MANUAL_REQUESTED` when the flag is absent but does not write `unset MANUAL_REQUESTED`. Re-sourcing the rewritten file in the same shell after a previous true value can leave stale manual mode active, while existing tests only validate fresh-subshell behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-session-env-manual-propagation-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: Gate B mode precedence is spread across three layers
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Gate B mode resolution depends on session env, in-memory `manual_requested`, and `run-params.json`, making behavior harder to predict across subshell re-entry and doc surfaces.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: Router-flag recovery overwrites `manual_gate_b` instead of sticky OR merge
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-gate-b-mode-resolution-output.txt, dyn-apply-all-body-dedup-output.txt, dyn-session-env-manual-propagation-output.txt
- **Severity**: latent
- **Concern**: Step 0b jq recovery assigns `.manual_gate_b = $merge_m` while partition/brainstorm use OR semantics and some plan text expected `(.manual_gate_b == true or $merge_m)`. Depending on intended semantics, recovery can clear a previously persisted manual mode or documentation/tests can misrepresent the intended argv-authoritative overwrite behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-gate-b-mode-resolution-output.txt, dyn-apply-all-body-dedup-output.txt, dyn-session-env-manual-propagation-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: MANUAL_REQUESTED precedence is not mechanically enforced in Step 3.5
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Gate B precedence says `MANUAL_REQUESTED=true` wins, but Step 3.5 relies on prose rather than a mechanical mode resolver. A `/design --manual` run with failed `run-params` persistence or skipped env sourcing could auto-apply if the orchestrator only reads `run-params.json`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

