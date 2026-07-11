---LARCH-REJECTED-BEGIN---
## Considered Plan Review Suggestions (Not Adopted)

These reviewer suggestions were considered but not adopted. Some may already be addressed by the current plan; they are not automatically unimplemented gaps.

### [Plan Review] FINDING_2

### FINDING_2: Bind expected assessment kinds using canonical adapter normalization
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: Post-adapter validation must compare requested kinds against a canonical, adapter-ordered binding rather than raw `DETAIL` or `DETAIL_FILE` text. A valid handoff such as `DETAIL=guidelines,invariants` can be normalized by the adapter to `invariants,guidelines`; comparing against raw order would reject a successful run and route it to tool failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In the shared adapter validation block, require the orchestrator to compute expected kinds with the same normalization rules as the frozen adapter (order, dedupe, allowed tokens) and compare that canonical set/string to adapter `ASSESSMENT_REQUESTED_KINDS` and `ASSESSMENT_RESULTS` coverage; forbid direct comparison to pre-adapter `DETAIL`/`DETAIL_FILE` text
  - From Cursor-Pragmatic: In the normalization and validation sections, bind expected kinds once (legacy alias synthesis or combined-route canonicalization) using the same ordering rules as the frozen adapter, and compare terminal ASSESSMENT_REQUESTED_KINDS only to that bound value; forbid raw DETAIL or DETAIL_FILE string equality
  - From Cursor-Requirements: During pre-adapter normalization, bind EXPECTED_ASSESSMENT_REQUESTED_KINDS using the same split/trim/duplicate-reject rules plus canonical invariants,guidelines ordering the adapter uses; compare adapter ASSESSMENT_REQUESTED_KINDS to that binding only. State explicitly that raw DETAIL order is not the validation key.
  - From Cursor-Requirements: During pre-adapter normalization, bind an expected kind list using the same split/trim/duplicate-reject rules and canonical `invariants,guidelines` ordering the adapter uses. Compare `ASSESSMENT_REQUESTED_KINDS` only to that binding. Say explicitly that raw `DETAIL` order is not the validation key. This closes the remaining gap from round 1 FINDING_2.


### [Plan Review] FINDING_3

### FINDING_3: Require explicit per-kind `ASSESSMENT_RESULTS` validation
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: Terminal validation is described in terms of status and abstract completeness, but does not explicitly require parsing `ASSESSMENT_RESULTS` and verifying coverage for every requested kind. A status-only check could relaunch ship after a partial result envelope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add `ASSESSMENT_RESULTS` to the mandatory terminal KV checklist in SKILL.md and require per-requested-kind `kind:state` coverage validation before the single `step-8-ship.sh` relaunch
  - From Cursor-Pragmatic: Add ASSESSMENT_RESULTS to the required terminal KV checklist and require coverage for every normalized requested kind per the frozen step-8-assessment.md contract before relaunching step-8-ship.sh
  - From Cursor-Requirements: Add ASSESSMENT_RESULTS to the SKILL.md and test-architectural-guidelines-step.sh validation pin list, requiring one kind:state token per requested kind in canonical order before the single ship relaunch.
  - From Cursor-Requirements: Add `ASSESSMENT_RESULTS` to the SKILL.md terminal validation list and to `test-architectural-guidelines-step.sh` pins, requiring one `kind:state` token per requested kind before ship relaunch.


---LARCH-REJECTED-END---
