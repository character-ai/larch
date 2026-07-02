### [rejected] FINDING_1

**Rejected subtype:** dismissed (0 YES)

### FINDING_1: New necessity gates change specialist filtering
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-reviewer-contracts
- **Severity**: important
- **Concern**: The compressed necessity-gate sections were added to previously gate-less hand-maintained specialists, changing in-scope vs OOS behavior and conflicting with the zero-behavior-change acceptance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Revert gate on agents that did not have it, or explicitly accept and re-baseline voting calibration.
  - From cursor-specialist-edge-cases: Document the intentional behavior expansion in the PR, or add/extend a harness asserting specialist necessity-gate text stays semantically aligned with review-acceptance-rubric.md.
  - From cursor-specialist-testing: Confirm intentional alignment with generated agents; if not, revert gate additions for previously gate-less specialists.
  - From dyn-dyn-reviewer-contracts: Either document this as an intentional rubric-alignment behavior change and update acceptance criteria, or keep necessity-gate compression only on reviewers that already had the section and leave correctness/security/structure without a newly introduced gate.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** dismissed (0 YES)

### FINDING_2: Compressed necessity-gate scoring lost calibration
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-reviewer-contracts
- **Severity**: important
- **Concern**: The compressed necessity-gate boilerplate dropped explicit scoring mechanics, including -0.25/-1 penalties, provisional OOS +1, /analyze-issues docking, and the optional-test carve-out guard. That leaves reviewers with weaker calibration than the full Code Reviewer rubric and diverges from the old prompt.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Restore dropped scoring/OOS sentences inside each block; compress other prose only.
  - From cursor-specialist-edge-cases: Restore scoring sentences in the compressed necessity-gate boilerplate across all specialist template sections and mirrored agents/pre-rendered bodies.
  - From cursor-specialist-testing: Keep a one-line pointer to review-acceptance-rubric.md or verify competition notice is always injected.
  - From dyn-dyn-reviewer-contracts: Restore the minimum scoring phrases in the compressed one-liner (provisional OOS +1, analyze-issues dock caveat, -0.25/-1 detail) or hoist scoring text into the renderer-injected competition notice so all specialists see identical calibration language.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** dismissed (0 YES)

### FINDING_3: Do not trim mandatory failing scenarios
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing
- **Severity**: important
- **Concern**: The prose-length cap no longer explicitly forbids trimming mandatory concrete failing scenarios. That can encourage reviewers to shorten required failing scenarios just to fit the sentence cap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Restore verbatim mandatory-scenario sentence in all specialist output-format sections.
  - From cursor-specialist-testing: Reintroduce the never-trim-scenario guard in compressed form across all compressed specialist bodies.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** dismissed (0 YES)

### FINDING_7: TDD severity semantics changed
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: important
- **Concern**: The test-coverage / TDD wording now caps missed-TDD findings at Nit only. That can down-rank TDD gaps that previously could have been reported at higher severity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Confirm intentional alignment with Code Reviewer line 67; otherwise restore prior TDD wording for this specialist only.
  - From cursor-specialist-testing: Restore original TDD severity semantics and compress only surrounding prose, or explicitly document the policy change.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** dismissed (0 YES)

### FINDING_8: Plan-required artifact carve-out expands edge-cases/testing scope
- **Reviewer(s)**: dyn-dyn-reviewer-contracts
- **Severity**: important
- **Concern**: Adding `Explicitly plan-required omitted artifacts are In-Scope; cite the plan.` to edge-cases/testing changes their necessity-gate filtering. Those reviewers can now file plan-omission findings as in-scope where they previously would not.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-reviewer-contracts: If parity with pre-compression edge-cases/testing behavior matters, drop the plan-required-artifacts sentence from those two specialists while keeping it on plan-fidelity and other generated reviewers where it existed before.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

