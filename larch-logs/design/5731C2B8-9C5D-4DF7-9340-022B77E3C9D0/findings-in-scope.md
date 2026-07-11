### FINDING_1: Update fence-shape tests for the adapter-only Step 8 flow
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Concern**: The plan updates plan/fence counts but does not remove legacy compose-write ordering assertions. The harness may still require per-kind compose writers and a guidelines-only relaunch, causing the approved adapter-only Step 8 flow to fail CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Extend the `scripts/test-implement-fence-shape.sh` plan item to replace those slices with adapter-first checks: one `step-8-assessment.sh` launcher through `implement-run-$PPID.sh`, no prompt-side assessment start/wait pair, and exactly one post-validation `step-8-ship.sh` relaunch

### FINDING_2: Bind expected assessment kinds using canonical adapter normalization
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: Post-adapter validation must compare requested kinds against a canonical, adapter-ordered binding rather than raw `DETAIL` or `DETAIL_FILE` text. A valid handoff such as `DETAIL=guidelines,invariants` can be normalized by the adapter to `invariants,guidelines`; comparing against raw order would reject a successful run and route it to tool failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In the shared adapter validation block, require the orchestrator to compute expected kinds with the same normalization rules as the frozen adapter (order, dedupe, allowed tokens) and compare that canonical set/string to adapter `ASSESSMENT_REQUESTED_KINDS` and `ASSESSMENT_RESULTS` coverage; forbid direct comparison to pre-adapter `DETAIL`/`DETAIL_FILE` text
  - From Cursor-Pragmatic: In the normalization and validation sections, bind expected kinds once (legacy alias synthesis or combined-route canonicalization) using the same ordering rules as the frozen adapter, and compare terminal ASSESSMENT_REQUESTED_KINDS only to that bound value; forbid raw DETAIL or DETAIL_FILE string equality
  - From Cursor-Requirements: During pre-adapter normalization, bind EXPECTED_ASSESSMENT_REQUESTED_KINDS using the same split/trim/duplicate-reject rules plus canonical invariants,guidelines ordering the adapter uses; compare adapter ASSESSMENT_REQUESTED_KINDS to that binding only. State explicitly that raw DETAIL order is not the validation key.
  - From Cursor-Requirements: During pre-adapter normalization, bind an expected kind list using the same split/trim/duplicate-reject rules and canonical `invariants,guidelines` ordering the adapter uses. Compare `ASSESSMENT_REQUESTED_KINDS` only to that binding. Say explicitly that raw `DETAIL` order is not the validation key. This closes the remaining gap from round 1 FINDING_2.

### FINDING_3: Require explicit per-kind `ASSESSMENT_RESULTS` validation
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: Terminal validation is described in terms of status and abstract completeness, but does not explicitly require parsing `ASSESSMENT_RESULTS` and verifying coverage for every requested kind. A status-only check could relaunch ship after a partial result envelope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add `ASSESSMENT_RESULTS` to the mandatory terminal KV checklist in SKILL.md and require per-requested-kind `kind:state` coverage validation before the single `step-8-ship.sh` relaunch
  - From Cursor-Pragmatic: Add ASSESSMENT_RESULTS to the required terminal KV checklist and require coverage for every normalized requested kind per the frozen step-8-assessment.md contract before relaunching step-8-ship.sh
  - From Cursor-Requirements: Add ASSESSMENT_RESULTS to the SKILL.md and test-architectural-guidelines-step.sh validation pin list, requiring one kind:state token per requested kind in canonical order before the single ship relaunch.
  - From Cursor-Requirements: Add `ASSESSMENT_RESULTS` to the SKILL.md terminal validation list and to `test-architectural-guidelines-step.sh` pins, requiring one `kind:state` token per requested kind before ship relaunch.

### FINDING_4: Rewrite durable handoff prose to enforce one combined adapter route
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements
- **Severity**: major
- **Concern**: The durable handoff paragraph still describes independent legacy relaunches and main-agent consumption of materialized assessment diffs. That contradicts the single combined adapter invocation and one post-validation ship relaunch, leaving an inline-authorship escape hatch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add an explicit `ship-pr-exit-matrix.md` task to rewrite the durable handoff paragraph so all three assessment tokens normalize to `NEXT_ACTION=assessments`, invoke the combined adapter once, validate its envelope, and relaunch ship once; remove independent back-compat relaunch and materialized-diff authorship language
  - From Cursor-Requirements: Rewrite the durable handoff paragraph to state that all assessment tokens normalize to NEXT_ACTION=assessments, the adapter owns assessment work from existing materialization inputs, legacy aliases do not relaunch independently, and only one post-validation step-8-ship.sh relaunch is allowed. Add a harness negative assertion against relaunch independently and main-agent materialized-diff consumption prose.
  - From Cursor-Requirements: Extend the `ship-pr-exit-matrix.md` update to rewrite line 37: all assessment tokens normalize to the combined adapter; the adapter consumes existing materialization inputs; legacy aliases do not relaunch independently. Add a negative harness assertion against `relaunch independently` and main-agent materialized-diff consumption language.

### FINDING_5: Specify executable, atomic normalization for legacy assessment aliases
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Concern**: Alias normalization is specified only as prose, without a concrete operation or focused verification. Legacy aliases could reach the adapter unchanged, or normalization could drop unrelated handoff keys, reproducing the compatibility defect.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add an explicit normalization operation that atomically preserves all unrelated handoff keys, rewrites only `NEXT_ACTION` and the canonical `DETAIL`, and routes malformed input to the existing Tool Failures hard stop. Add a focused test that exercises the three handoff shapes rather than only asserting prompt wording.
