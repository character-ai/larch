### [rejected] FINDING_14

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_14: Post-revision sizing can bypass Step 2b.5 hard gate
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: After plan-review revision, sizing uses `check-plan-size` only; self-declared `mechanical_churn` / `diff_added` can suppress `HARD_TRIGGER_FIRED` without Step 2b.5 Split/Cancel. A plan can pass Step 2b.5 with small `diff_lines`, then revision rewrites to 5000+ lines with `mechanical_churn: true` and avoid `LOOP_STATUS=plan-size-trigger` with no human hard-gate prompt.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_15: mechanical_churn is a self-attested trust boundary
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `mechanical_churn: true` is self-attested and downgrades the enforced diff hard gate to advisory only; any design agent can label large plans mechanical to skip Split/Cancel on diff size without stronger assurance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: Deletion-heavy plans without diff_added operator footgun
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Deletion-heavy plans with only `diff_deleted` and high `diff_lines` still use legacy total-churn threshold behavior; operator may emit only `diff_deleted` relief values contrary to SKILL expectations for `diff_added` on deletion-heavy paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_17: optional-trailer-dedup-loss LOOP_REASON lacks clarity
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: On optional-trailer-dedup-loss, restoring the entire pre-revise plan after a successful revise can surface a generic `emit-plan-failed` outcome; `LOOP_REASON` does not clearly distinguish dedup trailer collision from other emit failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_18: SKILL.md Gate B preservation not script-enforced before EMIT_PLAN
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `SKILL.md` lists Gate B / Gate A direct-rewrite trailer preservation, but implementation only adds Step 2b emit plus Step 2b.5 parse/advisory, delegating preservation to reference docs. Operators following Step 2b alone may rewrite `plan.txt` without snapshot/validate before `EMIT_PLAN`; prompt-side Gate B write paths lack script enforcement until 2b.5.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: Repeated per-key awk parses during trailer validation
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `plan_has_optional_trailer_key` re-parses the plan with nested awk per key in `revise-plan-with-waterfall.sh`, adding extra process spawns on every tier attempt as candidate count grows.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

