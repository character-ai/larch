### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: Driver-rendered WORSE prose remains semantically untrusted to the orchestrator
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Trailer spoofing is mitigated, but the WORSE block itself is still echoed into the orchestrator LLM. Crafted assessor prose could attempt semantic prompt injection even without controlling trusted trailers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_17: rc=10 trailer parsing uses an unquoted heredoc that can execute command substitutions
- **Reviewer(s)**: dyn-shell-fence-output.txt
- **Severity**: important
- **Concern**: The Step 3.6 fence feeds trusted trailers through an unquoted heredoc. If a trailer value contains command substitution, Bash can execute it during parsing; `ROUND_NUM` is not validated as digits-only before trailer emission.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-fence-output.txt: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_18: Invalid rc=10 trailer abort hides the driver-rendered display
- **Reviewer(s)**: dyn-shell-fence-output.txt
- **Severity**: latent
- **Concern**: On missing or invalid trusted trailers, the fence exits before echoing the pre-marker display. Operators see only the fail-closed stderr banner, losing the driver-rendered WORSE context already present in captured output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-fence-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_20

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_20: Pause/resume tests do not cover post-3b bypass progression
- **Reviewer(s)**: dyn-pause-resume-output.txt
- **Severity**: latent
- **Concern**: Current bypass tests assert resume at 3b with bypass sentinels present, but do not simulate completing 3b and pausing again to ensure the next resume advances to Step 4 rather than re-entering Gate B or Step 3.6.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-pause-resume-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_21: Mid-WORSE pause reruns assessment instead of restoring pending decision
- **Reviewer(s)**: dyn-pause-resume-output.txt
- **Severity**: latent
- **Concern**: If rc=10 occurs and the operator pauses before Continue/Stop, only `step-3.5` is complete. Resume reruns the full HARD assessor rather than restoring the pending decision, potentially duplicating work or changing the verdict.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-pause-resume-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: Trailer parsing logic is duplicated between SKILL and harness
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Trusted trailer parsing exists in both the Step 3.6 fence and the handoff harness. Future validation changes must be edited in lockstep, risking drift that could break spoof protection or fail-closed behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: Assessor machine KVs are printed into user-facing chat
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `ASSESSOR_RC` and `ASSESSOR_ROUND_NUM` are echoed alongside display output, mixing machine-readable handoff lines with operator-facing WORSE copy despite the FD-3/display split.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: Step 3.6 lacks a start breadcrumb comparable to peer steps
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Step 3.6 does not clearly print an orchestrator-owned start breadcrumb before the cheap gate. SIMPLE runs may only show a skip line, while HARD runs depend on driver output for visibility.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: Resume ladder hardcodes fractional step ordering
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `design-pause-save.sh` hardcodes the `3 -> 3.5 -> 3.6 -> 3b` resume ladder before registry scanning. Future fractional steps will require more bespoke branches or risk wrong resume targets.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

