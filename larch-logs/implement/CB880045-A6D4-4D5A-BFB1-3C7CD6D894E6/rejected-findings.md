### [rejected] FINDING_6

**Rejected subtype:** dismissed (0 YES)

### FINDING_6: step-16-17-sentinel.md documents retired inline emit contract
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-dyn-final-summary-contract-output.txt
- **Severity**: important
- **Concern**: `skills/implement/references/step-16-17-sentinel.md` lines 25–27 still document the retired inline contract (“verbatim full-body emission of the extracted marker body defined in Step 17”) and falsely claim the harness requires that sentence in `skills/implement/SKILL.md`. Contributors debugging Step 16–17 may reintroduce inline extraction or expect a harness pin that no longer exists; authoritative contracts are `skills/implement/SKILL.md` plus `skills/shared/final-summary-emit.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Rewrite the permitted-text section to reference skills/shared/final-summary-emit.md and the current NEVER #17 harness pin.
  - From dyn-dyn-final-summary-contract-output.txt: Rewrite the “Permitted post-summary orchestrator text” section to point at the shared marker-first profile with the same Step 17 / Step 18b bindings as NEVER #17, or delete the contradictory excerpt and state explicitly that `skills/implement/SKILL.md` plus `skills/shared/final-summary-emit.md` are the only authoritative contracts.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

