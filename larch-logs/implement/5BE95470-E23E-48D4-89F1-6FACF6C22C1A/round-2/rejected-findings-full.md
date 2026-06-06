### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: Phase 7 inverts sentinel semantics from success boundaries to host entry
- **Reviewer(s)**: dyn-artifact-allow-ordering-output.txt
- **Severity**: latent
- **Concern**: Phase 7 moves absorbed completion sentinels from step success boundaries to host entry fences (before pause-check). For the folded discussion block batched at Step 2a entry, a pause/crash after the entry fence but before sketch/plan LLM work completes still leaves those markers set, so `design-pause-save.sh` resumes forward instead of replaying in-flight discussion/sketch work—a regression versus pre-Phase 7 sentinel semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-artifact-allow-ordering-output.txt: Either (a) restrict pre-work batch writes to idempotent **repair** paths only (no-brainstorm repair, backward re-entry) and keep first-time discussion markers at true success boundaries, or (b) add a parallel "in-progress" marker (e.g. `.completed/step-2a.pending`) that pause-save consults before treating folded steps as done.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: No-brainstorm discussion span lacks pause-check Bash boundary
- **Reviewer(s)**: dyn-artifact-allow-ordering-output.txt
- **Severity**: latent
- **Concern**: With brainstorm off, pure-LLM Steps 1c, 1d, 1d.7, and 1e have no Bash boundary with pause-check between Step 0c and Step 2a entry (Step 1d.5 prelude is skipped). A `/pause` during that entire discussion/outline span cannot be honored until Step 2a entry—potentially many LLM turns later. This is the largest structural pause-latency gap and is not covered by `assert_bash_fences_have_pause_check` because those steps no longer have fences.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-artifact-allow-ordering-output.txt: Accept explicitly in the audit table as a named exception, or retain a single lightweight "folded discussion checkpoint" Bash fence after Step 1d.7 (source-env + pause-check only, no timing prelude) for the no-brainstorm route so pause latency is bounded without reintroducing per-step preludes.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: HARD prelude sentinels written before phase work completes
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: HARD paths write `step-2a` at the Step 2a.5 prelude and `step-2a.5` at the Step 2b prelude before dialectic/plan work completes. Pause or crash after the prelude but before work finishes marks phases complete and suppresses replay on resume.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Defer HARD sketch/dialectic sentinels to success boundaries or add artifact-gated resume checks.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: Folded sentinels widen pause window; step-4b marked before OOS filing
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Folded sentinels widen pause latency. The Step 5 prelude marks `step-4b` complete before OOS filing (5b). A crash between the Step 5 prelude and 5b can misrepresent finalize progress, and the widened LLM-only pause window prolongs exposure of sensitive discussion content.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Document tradeoff in SECURITY.md; keep step-4b boundary-local; ensure publish routing requires step-5b not step-4b alone.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_8: HARD degraded zero-sketch sentinel naming diverges from plan
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: The HARD zero-sketch degraded path uses `NO_SKETCHES_DEGRADED_HARD` instead of the plan-implied `NO_SKETCHES_CLASSIFIED_SIMPLE`. Plan readers and tooling keyed only on the SIMPLE sentinel may mis-classify degraded HARD runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Document NO_SKETCHES_DEGRADED_HARD in plan edge cases and add a harness pin that HARD degraded synthesis must not equal NO_SKETCHES_CLASSIFIED_SIMPLE


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_9: design-pause-load.sh change split across commits from docs update
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Phase 7 commit updates `design-pause-load.md` but not the script; the script change lives in prior commit `480c8ba4b`. PR reviewers may think pause-load clearing is docs-only while behavior changed on an earlier commit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Reference #3529 in the Phase 7 PR or include the script change in the same deliverable commit


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

