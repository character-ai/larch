# Review Round 1

- Mode: `diff`
- 13 accepted, 5 rejected (5 exonerated)

## Accepted Findings

### FINDING_1: design-outline scope omits Q&A-only exclusion
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `design-outline.md` does not state that ad-hoc Q&A-only `/design` exits are excluded from the outline approval path, so operators loading only that reference may apply the outline gate too broadly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_14: render-final-summary caller count is stale
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `render-final-summary.md` still says eleven callers after adding the `cancelled-outline` caller, leaving contributor-facing summary outcome documentation miscounted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_16: Step 1d sprawl return still routes to Gate A
- **Reviewer(s)**: dyn-cross-doc-sync-output.txt, dyn-sentinel-lifecycle-output.txt
- **Severity**: important
- **Concern**: The Split-path “Refine plan myself” return table still routes Step 1d sprawl to Step 1e Gate A, which is now post-plan re-entry-only and can bypass outline approval on a pre-plan path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cross-doc-sync-output.txt: Address the concern above.
  - From dyn-sentinel-lifecycle-output.txt: Address the concern above.


### FINDING_17: approval-gates header contradicts re-entry-only Gate A
- **Reviewer(s)**: dyn-cross-doc-sync-output.txt
- **Severity**: important
- **Concern**: `approval-gates.md` still says Gate A always prompts, conflicting with the new first-time Step 1d.7 outline gate and Gate A’s re-entry-only role.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cross-doc-sync-output.txt: Address the concern above.


### FINDING_2: Step 1e can run Gate A on pre-plan control flow
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-cross-doc-sync-output.txt
- **Severity**: important
- **Concern**: Step 1e’s banner/body can still execute on first-time or missing-outline pre-plan paths where Gate A should be skipped or control should return to Step 1d.7, risking Shape 2 execution without `plan.txt` and violating the outline-first flow.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-cross-doc-sync-output.txt: Address the concern above.


### FINDING_21: cancelled-outline fallback summary orders notes before sentinel
- **Reviewer(s)**: dyn-shell-interface-output.txt
- **Severity**: important
- **Concern**: `compose_self_fallback` emits the `cancelled-outline` cancel-site note before the run-summary sentinel, unlike the primary renderer contract where note lines are appended after the sentinel.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-interface-output.txt: Address the concern above.


### FINDING_24: Step 1d.7 approved sentinel can re-enter sketches after plan exists
- **Reviewer(s)**: dyn-sentinel-lifecycle-output.txt
- **Severity**: important
- **Concern**: The Step 1d.7 guard routes any `.outline-approved` session to Step 2a, even when `plan.txt` already exists, so resumed or replayed post-plan flows can incorrectly re-enter sketches instead of staying in the post-plan gate path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-sentinel-lifecycle-output.txt: Address the concern above.


### FINDING_25: Step 2a/2b treat draft outline as approved without sentinel
- **Reviewer(s)**: dyn-sentinel-lifecycle-output.txt
- **Severity**: important
- **Concern**: Step 2a and Step 2b use any non-empty `design-outline.md` as approved binding context without checking `.outline-approved`, so canceled or draft outline content can be injected if control reaches those steps incorrectly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-sentinel-lifecycle-output.txt: Address the concern above.


### FINDING_26: Sentinel lifecycle is underspecified
- **Reviewer(s)**: dyn-sentinel-lifecycle-output.txt
- **Severity**: important
- **Concern**: `design-outline.md` does not explicitly state that `.outline-approved` is written only on Approve, never on Refine/Cancel, nor does it document recovery from stale sentinel/session state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-sentinel-lifecycle-output.txt: Address the concern above.


### FINDING_4: Approve outline lacks required acknowledgment breadcrumb
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The Approve outline path writes `.outline-approved` and proceeds to sketches without the brief operator-visible acknowledgment required by acceptance criteria.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_5: cancelled-outline is missing from post-publish outcome matrix
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-shell-interface-output.txt
- **Severity**: important
- **Concern**: The exhaustive post-publish summary outcome matrix omits `cancelled-outline`, leaving title/outcome/stdout parity and cancel-site note behavior undercovered compared with other legal cancel outcomes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From dyn-shell-interface-output.txt: Address the concern above.


### FINDING_6: Structure tests do not pin Step 2a/2b outline propagation
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Check 2974 does not pin the SKILL.md Step 2a/2b prose that prepends or reads `design-outline.md`, so future edits could silently remove load-bearing outline propagation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_8: design-outline publish contract is false
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `design-outline.md` claims it is excluded from design-log publish bundles, but `design-log-publish.sh` publishes top-level session artifacts through redaction, creating a misleading security expectation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


