### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: Session-cache banner test only matches a partial prefix
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Check 26 can pass even if the refusal banner loses its wait, override, or delete instructions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Grep full banner literal or additional required substrings.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: Step 0b structural check can pass without executable guard wiring
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Check 24 can pass on prose mentions of `design_reentry_marker_hit`, without proving the guard is wired in an executable Bash block.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Anchor check on _reentry_out= or source line inside Step 0b fence.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_15: Guard key uses volatile shell `PPID` instead of stable Claude pid
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Marker write and hit both use shell `$PPID`; nested Bash invocations can change that value between Step 5c and Step 0b, causing the guard to miss.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Use the same claude-pid variable written by write-design-current-env for both write and hit; pin in test-design-structure.sh.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: Five-minute TTL admits delayed spurious re-entry
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: After the 300-second TTL expires, a delayed re-entry on an untagged issue with a plan can still be admitted, so the original symptom can recur outside the TTL window.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Extend TTL, refresh policy, or narrow acceptance to gap case within TTL; document late re-entry limitation.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_17: Step 5c marker write is prose-only
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The marker write is not pinned in a fenced Bash block, so an orchestrator can omit it and leave the guard ineffective.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add fenced 5.5 block with prelude + write call, or structural harness pin for mandatory execution pattern.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: Final-summary marker path reconstruction can drift or use the wrong fallback
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-integration-contract-output.txt
- **Severity**: important
- **Concern**: `render-final-summary.sh` duplicates the marker-path grammar and references a fallback PPID variable that is not set on the branch. If guard state is not carried across shell boundaries, the cancelled-reentry summary can render `Marker: N/A` or reconstruct the wrong path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Source lib and call design_reentry_marker_path when env unset.
  - From dyn-integration-contract-output.txt: Extend the fallback to `${LARCH_DESIGN_REENTRY_GUARD_PPID:-${DESIGN_REENTRY_GUARD_PPID:-$PPID}}` and/or call `design_reentry_marker_path` when `ISSUE_NUMBER` is set, so the renderer self-heals without relying on non-persisted exports.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_20

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_20: Guard-hit tmpdir preservation wording omits the cleanup invariant
- **Reviewer(s)**: dyn-prompt-orchestrator-output.txt
- **Severity**: nit
- **Concern**: The guard-hit path says to preserve `$DESIGN_TMPDIR` but does not explicitly mirror the sibling refusal wording that Step 6 cleanup is gated on `PLAN_WRITE_OK=true`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prompt-orchestrator-output.txt: Mirror line 190’s parenthetical on sub-step 2.6 step 3: e.g. “`$DESIGN_TMPDIR` is preserved (Step 6 cleanup gates on `PLAN_WRITE_OK=true`; it is unset on this path).”


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: Reference Bash KV parser duplicates the library contract
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The large Bash parser example in `SKILL.md` repeats the helper contract and can drift from `lib-design-reentry-guard.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Trim reference block; rely on lib-design-reentry-guard.md contract.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: Marker write before `PLAN_WRITE_OK=true` can block retry after crash
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Step 5.5 writes the marker before setting `PLAN_WRITE_OK=true`; a crash between those steps can make a retry hit the session-cache refusal even though the completed-run flag was never set.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Document intentional friction or gate marker write on PLAN_WRITE_OK if product wants otherwise.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_8: No end-to-end test ties marker write to Step 0b refusal
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Current tests cover unit behavior and structure, but not a full flow where Step 5c writes a marker and the next Step 0b invocation refuses.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add integration-style harness: write marker then hit; or design-driver two-entry simulation.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: Marker write failure path is untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The planned `MARKER_WRITE_FAILED` / `append-tool-failure` path lacks a filesystem-failure fixture, so a regression that leaves no marker may not be caught.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add fixture with failing mkdir/touch; assert stderr KV and non-zero rc.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

