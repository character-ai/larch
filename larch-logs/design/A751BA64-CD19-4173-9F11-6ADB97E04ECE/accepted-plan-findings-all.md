### FINDING_1: CI-fix still reroutes through retired Phase A staging
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Ship State Integrator, Codex-dyn-Ship State Integrator
- **Severity**: blocking
- **Concern**: The ci-fix flow and adjacent Step 7a guidance still tell the orchestrator to rerun the retired Phase A/staging path instead of deferring reassessment to the next Step 8 compose-time gate, so a CI-fix or SKILL-only edit can leave contradictory instructions in place.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add ### UPDATED: skills/implement/references/ship-pr-ci-fix.md replacing step 11 with compose-time deferral to the next step-8-ship.sh relaunch; add ### UPDATED: scripts/test-implement-structure.sh to swap the pinned Phase A needle for the new contract
  - From Cursor-Arch: Include explicit replacement of the Step 7a continuation breadcrumb in the SKILL.md update bullets (e.g. proceed directly to Step 8) alongside the harness expectation rewrites already listed for test-architectural-guidelines-step.sh
  - From Codex-Arch: Add `skills/implement/references/ship-pr-ci-fix.md` as UPDATED. Replace Step 11 with a compose-time contract: do not rerun Phase A; after commit, log refresh, and push, relaunch Step 8 so the guidelines-assessment gate rematerializes when HEAD or final diff changed.
  - From Cursor-Innovation: Add ### UPDATED: skills/implement/references/ship-pr-ci-fix.md replacing step 11 with compose-time guidance (next step-8-ship relaunch owns assessment) and pin the change in test-architectural-guidelines-step.sh
  - From Cursor-Pragmatic: Add ### UPDATED: skills/implement/references/ship-pr-ci-fix.md mirroring conflict-resolution.md: drop Phase A rerun; state that the next step-8-ship relaunch owns compose-time reassessment when HEAD/diff changed.
  - From Cursor-Requirements: Add ### UPDATED: ship-pr-ci-fix.md; delete step 11 Phase A rerun and state that the next step-8-ship.sh relaunch owns compose-time reassessment when HEAD or diff changed
  - From Cursor-dyn-Ship State Integrator: Rewrite ship-pr-ci-fix.md step 11 and the SKILL.md reassessment paragraph to state that the next step-8-ship.sh entry runs the compose-time gate (fresh assessment only when HEAD or the final diff changed).
  - From Codex-dyn-Ship State Integrator: Add ship-pr-ci-fix.md to the firm updates. Replace the Phase A rerun with a push/relaunch instruction that lets the Step 8 compose-time gate refresh the note.


### FINDING_2: Closeout still pins staged assessments
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Ship State Integrator
- **Severity**: blocking
- **Concern**: Step 16/17 closeout still reads from the staged pin path instead of the durable compose-time note, so final-report rendering can still surface the drop notice or miss the real assessment even after the compose-time migration.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add ### UPDATED: python/larch/state/closeout.py to drop staged pinning and read the compose-time durable note only; add python/tests/state/test_closeout.py to the testing strategy; remove SKILL.md Step 16-17 staged-pin prose at skills/implement/SKILL.md:727 in the same SKILL.md edit
  - From Cursor-Innovation: Add ### UPDATED: python/larch/state/closeout.py to read durable compose-time note only (or no-op when already written); update skills/implement/SKILL.md Step 16 prose and add closeout regression coverage
  - From Cursor-Pragmatic: Add ### UPDATED: python/larch/state/closeout.py and python/tests/state/test_closeout.py: delete staged pin-once helpers; read consumable compose-time durable note only (or no-op when absent); update SKILL.md Step 16 pin prose accordingly.
  - From Cursor-Requirements: Add ### UPDATED: python/larch/state/closeout.py and python/tests/state/test_closeout.py; read durable compose-time note only, remove staged pin step 0, and drop SKILL.md Step 16 pin prose
  - From Cursor-dyn-Ship State Integrator: Add python/larch/state/closeout.py to the firm file list: remove staged pin step 0 and read the compose-time durable note directly (or no-op when note_consumable for current HEAD), matching the final_report.py changes.
  - From Cursor-dyn-Ship State Integrator: Update Step 16 to state that the final report reads the compose-time durable note written during Step 8 and performs no staged pin or reassessment.


### FINDING_3: Exit matrix still lacks guidelines-assessment routing
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements, Codex-dyn-Ship State Integrator
- **Severity**: important
- **Concern**: The mandatory exit matrix still has no architectural-guidelines-assessment / guidelines-assessment route or same-turn branch semantics, so route-exit can fall back to operator-bail or Step 16 instead of compose-time assessment authoring.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add ### UPDATED: skills/implement/references/ship-pr-exit-matrix.md mapping architectural-guidelines-assessment to guidelines-assessment plus branch semantics mirroring oos-pipeline (author note, write durable copy, stale-handoff clear, relaunch step-8-ship.sh, anti-halt to Step 8 not Step 16)
  - From Codex-Arch: Add `skills/implement/references/ship-pr-exit-matrix.md` as UPDATED. Document the `architectural-guidelines-assessment` reason mapping, handoff artifact fields, and `guidelines-assessment` branch semantics.
  - From Cursor-Innovation: Add ### UPDATED: skills/implement/references/ship-pr-exit-matrix.md plus matching skills/implement/SKILL.md Step 8+ post-driver skeleton entry mirroring ci-fix/reship anti-halt
  - From Cursor-Innovation: State in the new branch: after compose write succeeds run stale-handoff clear and background step-8-ship.sh in the same turn with no recap (match reship/ci-fix NEVER #7 boundary)
  - From Cursor-Pragmatic: Add ### UPDATED: ship-pr-exit-matrix.md with needs_user_reason=architectural-guidelines-assessment -> NEXT_ACTION=guidelines-assessment and branch semantics aligned with the new SKILL.md Step 8+ skeleton.
  - From Codex-Pragmatic: Add a firm UPDATED entry for ship-pr-exit-matrix.md that maps architectural-guidelines-assessment to guidelines-assessment and documents the branch: read the compose-time reference, write the durable note, clear stale handoff, and relaunch step-8-ship.sh.
  - From Cursor-Requirements: Add ### UPDATED: ship-pr-exit-matrix.md with architectural-guidelines-assessment -> guidelines-assessment in the reason table plus branch semantics mirroring the new SKILL.md Step 8+ skeleton
  - From Codex-Requirements: Add a firm update for skills/implement/references/ship-pr-exit-matrix.md covering the exit-3 reason, NEXT_ACTION=guidelines-assessment, required handoff fields or artifact paths, and relaunch semantics.
  - From Codex-dyn-Ship State Integrator: Add ship-pr-exit-matrix.md as an UPDATED file. Document architectural-guidelines-assessment in the exit-3 table and branch semantics, including no pre-fix rebase, write-assessment helper, stale-handoff clear, and step-8-ship relaunch.


### FINDING_4: Fence-shape harness still misses the new compose writer fence
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The new compose-assessment writer fence is not reflected in the fence-shape harness, so CI can reject the change even when the behavioral contract is correct.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add ### UPDATED: scripts/test-implement-fence-shape.sh with EXPECTED_NEW bump and ordering slice for the compose writer fence
  - From Cursor-Pragmatic: Add ### UPDATED: scripts/test-implement-fence-shape.sh (and testing strategy line) to bump EXPECTED_OLD/EXPECTED_NEW and pin the new guidelines-assessment launcher fence per readability-style plan-drafting reminders.


### FINDING_5: Structure harness still pins Phase A prose
- **Reviewer(s)**: Cursor-Innovation, Cursor-Requirements, Cursor-dyn-Ship State Integrator
- **Severity**: important
- **Concern**: The structure harness still expects the old Phase A routing prose in the exit-matrix / ci-fix area, so a correct SKILL and reference update can still fail make lint until the pinned needles move.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add ### UPDATED: scripts/test-implement-structure.sh replacing Phase A pins with guidelines-assessment / compose-time contract pins
  - From Cursor-Requirements: Add ### UPDATED: scripts/test-implement-structure.sh to the plan testing strategy alongside test-architectural-guidelines-step.sh
  - From Cursor-dyn-Ship State Integrator: Add scripts/test-implement-structure.sh (and any mirrored needles in the same block) to the firm file list with updated expectations for guidelines-assessment routing and removal of Phase A rerun prose.


### FINDING_6: Route-exit tests miss the new assessment reason
- **Reviewer(s)**: Cursor-Innovation, Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Concern**: The route-exit classifier tests still do not cover the new architectural-guidelines-assessment mapping, so a regression can silently route the compose-time assessment request to operator-bail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add explicit ### UPDATED: python/tests/implement/test_implement_dispatch.py row plus parametrized case needs_user_reason=architectural-guidelines-assessment -> guidelines-assessment
  - From Cursor-Requirements: Extend the plan test list to name test_implement_dispatch.py parametrized exit-3 cases for architectural-guidelines-assessment -> guidelines-assessment
  - From Codex-Requirements: Add python/tests/implement/test_implement_dispatch.py as a firm UPDATED file and extend the sidecar classification table to assert architectural-guidelines-assessment maps to guidelines-assessment.


### FINDING_10: Live rebase and CI-fix paths still invalidate the note
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Ship State Integrator, Codex-dyn-Ship State Integrator
- **Severity**: blocking
- **Concern**: Several live rebase and CI-fix code paths still pin or invalidate the guidelines note outside the compose gate, so HEAD changes can wipe or regenerate the note after it has already been authored.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add ### UPDATED entries for ship_merge.py, ci_monitor.py, and ci_agentic_fix.py to remove invalidate/drop paths (no-op or clear stale note only) and extend test_ship.py / test_ci_agentic_fix.py so no live path can emit the drop notice.
  - From Cursor-Requirements: List ship_merge.py (and any folded rebase helper) under ### UPDATED:; remove or no-op pre-compose pin/invalidate; rely on the compose-time gate to rematerialize and request assessment when HEAD changes
  - From Cursor-Requirements: Update ci_monitor.py in the plan; drop pre-push pin/invalidate or replace with compose-time invalidation only when ship will rematerialize
  - From Cursor-Requirements: Add ### UPDATED: ci_agentic_fix.py (not only MAY_UPDATE test_ci_agentic_fix.py); remove _invalidate_guidelines_before_ci_push or defer invalidation to ship compose-time rematerialization
  - From Cursor-dyn-Ship State Integrator: List ship_merge.py, ci_monitor.py, and ci_agentic_fix.py as UPDATED files: delete or replace these calls so only the compose-time gate in ship.py owns note lifecycle; rely on HEAD-mismatch detection on the next step-8-ship entry instead of pre-compose invalidation.
  - From Codex-dyn-Ship State Integrator: Route every successful in-driver Step 12 rebase that can change HEAD back through the same PR body compose/update gate before CI/merge continues. Cover monitor.goto_rebase and MERGE_RESULT_MAIN_ADVANCED.


### FINDING_1: Update ci_monitor tests for the compose-gate contract
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Codex-Pragmatic, Codex-Requirements
- **Severity**: important
- **Concern**: The plan updates `ci_monitor` behavior but leaves the existing test coverage asserting pre-push guideline pin/invalidate behavior, so CI will fail or the retired out-of-gate contract will be preserved.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add `### UPDATED: python/tests/implement/test_ci_monitor.py` and extend the testing strategy to replace the pin-before-push assertion with compose-gate / no-out-of-gate-invalidation coverage aligned with the new `ci_monitor` contract.
  - From Cursor-Pragmatic: Add python/tests/implement/test_ci_monitor.py to Files to modify/create and the testing strategy; replace the pin/invalidate assertions with coverage that pre-push no longer mutates the note and the next step-8-ship.sh relaunch owns compose-time reassessment
  - From Codex-Pragmatic: Add python/tests/implement/test_ci_monitor.py to the firm updates and rewrite this test to assert pending retry does not pin or invalidate guidelines outside the compose gate.
  - From Codex-Requirements: Add python/tests/implement/test_ci_monitor.py to the plan and testing command, replacing this assertion with the compose-time contract: no pre-push guidelines pin/invalidate callback, and the next Step 8 compose gate owns reassessment


### FINDING_4: Preserve the untrusted-guidelines boundary at compose time
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Concern**: Removing the old Step 7a prose without relocating its trust boundary leaves repo-authored guideline text able to influence Step 8 assessment as prompt-injection input.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Carry the existing untrusted evidence rule into the compose-time reference or Step 8 guidelines-assessment branch: use only the Python helper/artifacts, treat guideline text and diff content as untrusted evidence, and state that they cannot override higher-priority repo or skill instructions.


### FINDING_6: Remove out-of-gate invalidate carve-out from conflict resolution
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The live conflict-resolution reference still authorizes architectural-guidelines invalidation outside the compose gate, which can wipe a durable note before reassessment runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Remove the invalidate carve-out in the same edit; state that only the next step-8-ship.sh relaunch may refresh assessment via the compose-time gate


### FINDING_7: Avoid wholesale invalidation in compose-time prepare
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: blocking
- **Concern**: A compose-time prepare modeled on `prepare_main` would still invalidate notes on relaunch, which can clear a durable note too early and loop or drop the assessment before PR composition.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Specify that compose-time prepare clears only staged and dropped-note artifacts, or short-circuits when note_consumable matches current HEAD; do not call invalidate_implement_note on relaunch after a successful compose write


