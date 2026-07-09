### FINDING_1: [OUT_OF_SCOPE] Extinct-token harness misses required acceptance tokens
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-bgjob-routing, cursor-specialist-plan-fidelity-auto
- **Severity**: major
- **Concern**: The extinct-token harness still covers only part of acceptance #1, so retired guard/env/prose can reappear outside larch-logs without failing CI; only the documented survivor paths should remain.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Extend the harness to check every acceptance #1 token with :!larch-logs and permit only bgjob-wait.md orchestrator-never.md and configuration-and-permissions.md survivors.
  - From codex-specialist-correctness: Add checks for every acceptance token, with explicit survivor handling.
  - From cursor-specialist-edge-cases: Add check_absent for every acceptance token or document intentional subset in plan/PR.
  - From codex-specialist-edge-cases: Add split-literal check_absent rows for every missing acceptance token.
  - From cursor-specialist-testing: Retired guard/env/prose can reappear outside larch-logs without failing make test-extinct-notification-stack or make test-harnesses. Add check_absent rows (or equivalent) for every acceptance token, preserving only the enumerated survivor paths.
  - From dyn-dyn-bgjob-routing: Extend extinct harness per finding 1 if broader token sweep is desired.
  - From cursor-specialist-plan-fidelity-auto: Add check_absent rows for every acceptance-criterion-1 token with the documented survivor carve-outs only.


Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_3: [OUT_OF_SCOPE] Duplicate `files:` key on `lint-bg-wait-coverage`
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-bgjob-routing
- **Severity**: minor
- **Concern**: Duplicate `files:` keys on `lint-bg-wait-coverage` silently make the last filter win, so the hook scope can drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Remove the duplicate files line.
  - From cursor-specialist-edge-cases: Remove the duplicate files line.
  - From cursor-specialist-testing: Remove the duplicate files line.
  - From dyn-dyn-bgjob-routing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_4: [OUT_OF_SCOPE] Predictable tmp-state write in hook can follow symlinks
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: minor
- **Concern**: The hook writes through a predictable tmp-state path and follows symlinks there, so same-user symlink tricks can redirect truncation to another writable file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Use a mktemp file plus symlink/non-regular checks and atomic replace, with temp cleanup on failure.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=true

### FINDING_5: [OUT_OF_SCOPE] Diagram mode still gates on legacy `.completed/step-4`
- **Reviewer(s)**: cursor-specialist-testing, cursor-specialist-plan-fidelity-auto
- **Severity**: major
- **Concern**: Step 5b.5 diagram mode still keys off the legacy `.completed/step-4` sentinel instead of the step-4 bgjob result env, and the remaining clear-list compatibility surfaces keep the old and new completion signals side by side.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Gate diagram on bgjob result env (BGJOB_RC=0 plus required KVs) or .step4-mode.env; update scripts/test-design-structure.sh:474.
  - From cursor-specialist-testing: Record KEEP/REPOINT in PR body or finish repointing diagram gate to result env only.
  - From cursor-specialist-testing: Align clear list with final Section E disposition once diagram gate is repointed.
  - From cursor-specialist-plan-fidelity-auto: Check bgjob/design-step4-tail.result.env (BGJOB_RC=0 plus required KVs) or .step4-mode.env instead of .completed/step-4.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### FINDING_6: Stale `_bg_wait_marker_context` baseline row remains
- **Reviewer(s)**: cursor-specialist-testing, cursor-specialist-plan-fidelity-auto, cursor-specialist-plan-fidelity-forced
- **Severity**: minor
- **Concern**: The env-via-config baseline still points at deleted `_bg_wait_marker_context`, leaving dead shrink-only drift in the ratchet.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Remove or regenerate the stale baseline entry.
  - From cursor-specialist-plan-fidelity-auto: Remove the _bg_wait_marker_context row or regenerate env-via-config-constant-baseline.json.
  - From cursor-specialist-plan-fidelity-forced: Delete the _bg_wait_marker_context object (lines 398-407), keeping the two _core_quiet_mirrors_to_fd4 rows


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_9: [OUT_OF_SCOPE] Daemon guidance dropped the verbatim `run_in_background` ban
- **Reviewer(s)**: cursor-specialist-plan-fidelity-auto, cursor-specialist-plan-fidelity-forced
- **Severity**: minor
- **Concern**: The authoritative daemon guidance no longer preserves the plan's verbatim `run_in_background` prohibition, so readers lose the exact rule even though enforcement still exists elsewhere.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-auto: Restore verbatim plan text or document and pin the intentional rewrite in tests.
  - From cursor-specialist-plan-fidelity-forced: Optionally restore the run_in_background:true prohibition sentence to the AGENTS.md daemon bullet


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_10: [OUT_OF_SCOPE] Step 6 in-flight check trusts any result env before registry
- **Reviewer(s)**: dyn-dyn-bgjob-routing
- **Severity**: minor
- **Concern**: `_step6_in_flight` returns "not in flight" as soon as any regular `design-step5c.result.env` exists, before registry liveness is consulted, so cleanup can run early on stale success state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-bgjob-routing: Reordering to check registry first would harden this.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_11: [OUT_OF_SCOPE] Transcript recapture skips success validation on file presence
- **Reviewer(s)**: dyn-dyn-bgjob-routing
- **Severity**: minor
- **Concern**: Transcript recapture is skipped whenever `bgjob/implement-step7a.result.env` exists, even if that env is empty or failed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-bgjob-routing: Address the concern above.
Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

