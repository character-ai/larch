# Review Round 1

- Mode: `diff`
- 2 accepted, 1 rejected (1 neutral)

## Accepted Findings

### FINDING_6: Step 18a.5 ordering pins absent from test-implement-structure.sh
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The plan-required Step 18a.5 ordering pin is absent from `scripts/test-implement-structure.sh` despite other Step 18 contract pins being added. A SKILL edit could run `step-18.sh --phase finalize` before Step 18a.5 or on the `STALL_RECOVERY_REQUIRED=true` path; escalation-success reporting would be skipped on happy/terminal paths and `make lint` would still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add `require(skill, ...)` pins for Step 18a.5 section presence, Do not run Step 18a.5 or --phase finalize on this path, Step 18a.5 runs before the finalize fence, and proceed without re-running --phase gate after terminal recovery.


### FINDING_9: SKILL.md:844 stale Step 17/18 handoff prose
- **Reviewer(s)**: dyn-step18-flow-output.txt
- **Severity**: important
- **Concern**: Step 17/18 handoff prose at `skills/implement/SKILL.md:844` still tells the orchestrator to parse `EMIT_BODY` / `WFR_RC` from `final-report step18b` stdout and emit `summary-final.md` directly when `EMIT_BODY=true`, but the branch moved Step 18 body emission into `step-18.sh --phase finalize` marker stdout and Step 18b section (lines 890–892) now requires marker extraction from captured finalize stdout with an explicit no-Read rule. An orchestrator that follows line 844 can skip marker extraction, attempt a post-teardown Read of `summary-final.md`, or emit outside the marker contract after teardown deletes `$IMPLEMENT_TMPDIR`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-step18-flow-output.txt: Rewrite line 844 to match the new contract: Step 18 status KVs and optional marker body come from captured `step-18.sh --phase finalize` stdout only; orchestrator re-emits the first balanced marker pair verbatim and uses `EMIT_BODY`/`WFR_RC` only for the missing-marker warning, not for direct body emission or Read fallback.


