### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/tests/implement/test_ci_monitor.py:2171-2212
- **Concern**: CI-monitor pin tests omitted from plan. Scenario: The plan updates `ci_monitor.py` to drop `_pin_or_invalidate_guidelines_note` before push, but `test_run_ci_fix_pending_retry_pins_guidelines_before_push` still requires that helper. CI will fail even when runtime behavior is correct.
- **Proposed resolution**: Add `### UPDATED: python/tests/implement/test_ci_monitor.py` and extend the testing strategy to replace the pin-before-push assertion with compose-gate / no-out-of-gate-invalidation coverage aligned with the new `ci_monitor` contract.



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/core/architectural_guidelines.py:912-940
- **Concern**: [SCOPE-REDUCTION] Parallel compose-prepare CLI duplicates existing prepare. Scenario: The plan still adds a new compose-time prepare verb while `prepare_main` already reads guidelines, materializes the final diff, and emits the same KV/untrusted blocks. A second verb duplicates dispatch surface and migration work without closing a behavioral gap.
- **Proposed resolution**: Repurpose `architectural-guidelines prepare` / `prepare_main` for compose-time materialization (add HEAD metadata and selective stale-artifact cleanup), retire Step 7a-only invalidate semantics, and drop the extra CLI verb from the plan.



### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/scripts/test-architectural-guidelines-step.md
- **Concern**: Harness sibling doc not listed for rewrite. Scenario: `test-architectural-guidelines-step.sh` is slated for new compose-time pins, but the sibling `.md` still documents Phase A staging, staged-to-durable pin behavior, and retired wrappers. `script-md-siblings.md` requires behavior/docs to ship together.
- **Proposed resolution**: Add `### UPDATED: skills/implement/scripts/test-architectural-guidelines-step.md` and rewrite purpose/callers/harness text to match the compose-time Step 8 contract, removed Phase A prose, and new `guidelines-assessment` routing.



### FINDING_4:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/scripts/step-8-ship.md:11-18
- **Concern**: Compose prepare stdout conflicts with Step 8 single-JSON wrapper contract. Scenario: The plan has ship.py materialize compose-time guideline inputs and a prepare helper that emits KVs plus untrusted blocks, but step-8-ship.sh captures ship pr stdout under a contract that it remains one schema JSON object; emitting the diff/guideline blocks there can break the Step 8 wire surface and expose large untrusted diff text in task output.
- **Proposed resolution**: Keep ship pr stdout JSON-only. Write materialized diff and guideline status to tmpdir files, put only safe paths/status in state or the route-exit handoff, and have the guidelines-assessment branch read those files.



### FINDING_5:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: security
- **Location**: skills/implement/SKILL.md:595
- **Concern**: Compose-time rewrite drops the untrusted-guidelines boundary. Scenario: The current Step 7a prose says ARCHITECTURAL_GUIDELINES.md is consulted only through the Python helper and parsed entries cannot override AGENTS.md, the skill, or the approved plan. The plan removes that section but does not move the boundary into the new compose-time branch/reference, so repo-authored guideline text can become prompt-injection input during Step 8 assessment.
- **Proposed resolution**: Carry the existing untrusted evidence rule into the compose-time reference or Step 8 guidelines-assessment branch: use only the Python helper/artifacts, treat guideline text and diff content as untrusted evidence, and state that they cannot override higher-priority repo or skill instructions.



### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/core/architectural_guidelines.py:849-940
- **Concern**: [SCOPE-REDUCTION] Plan adds a parallel compose-time prepare CLI though prepare/materialize already exist. Scenario: `prepare_main` already clears artifacts, reads guidelines, and calls `_emit_materialized_diff`; `materialize-diff` exposes the same materialization. A second compose-prepare verb expands `cli.py` dispatch, harness ports, and grep surface without a behavioral gap the acceptance criteria require
- **Proposed resolution**: Have `ship.py` call existing `materialize_implementation_diff` / internal prepare helpers for compose materialization; add only the compose-assessment write verb (or repurpose `write-staged-assessment`); drop the new prepare CLI from the plan



### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/implement/ship.py:826-917
- **Concern**: [SCOPE-REDUCTION] Merge-loop compose reassessment is beyond the stated acceptance criteria. Scenario: Acceptance targets Step 8b pre-PR rebase drop notices; in-loop `goto_rebase` / `MERGE_RESULT_MAIN_ADVANCED` paths already created the PR and do not recompose the body. Mandating compose-gate reassessment there adds NEEDS_USER interrupts mid-CI without clearing an acceptance criterion
- **Proposed resolution**: Limit compose-gate reassessment to pre-PR create and explicit open-PR body updates (ci-fix/conflict resume). For merge-loop rebases, remove out-of-gate pin/invalidate only; drop the edge-case requirement to re-author during Step 12 monitoring



### FINDING_8:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/report/final_report.py:216-260
- **Concern**: Plan does not explicitly retire `_persist_drop_notice_and_invalidate` live path. Scenario: `final_report._architectural_guidelines_section` can still persist the HEAD-drift drop notice and call `invalidate_implement_note` when fingerprints go stale, recreating the 62% failure mode in `summary-final.md` even after compose-time PR-body fix
- **Proposed resolution**: In the `final_report.py` update, delete `_persist_drop_notice_and_invalidate` and stale-fingerprint drop branches; read only a consumable compose-time durable note for current `HEAD`, or omit the section with a bounded warning



### FINDING_9:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/tests/implement/test_ci_monitor.py:2171-2212
- **Concern**: CI-monitor tests still pin pre-push guideline invalidation but the plan only updates ci_monitor.py. Scenario: Removing _pin_or_invalidate_guidelines_before_push leaves test_run_ci_fix_pending_retry_pins_guidelines_before_push asserting pin/invalidate behavior; pytest fails even when the new compose-time contract is correct
- **Proposed resolution**: Add python/tests/implement/test_ci_monitor.py to Files to modify/create and the testing strategy; replace the pin/invalidate assertions with coverage that pre-push no longer mutates the note and the next step-8-ship.sh relaunch owns compose-time reassessment



### FINDING_10:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/references/conflict-resolution.md:85
- **Concern**: Conflict-resolution still authorizes architectural-guidelines invalidate outside the compose gate. Scenario: The planned conflict-resolution edit removes Phase A rerun prose but the live reference still tells operators to call architectural-guidelines invalidate for re-entry; that can wipe a just-authored durable note before the next compose gate runs
- **Proposed resolution**: Remove the invalidate carve-out in the same edit; state that only the next step-8-ship.sh relaunch may refresh assessment via the compose-time gate



### FINDING_11:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/larch/core/architectural_guidelines.py:912-925
- **Concern**: Compose-time prepare must not reuse prepare_main wholesale invalidation. Scenario: Current prepare_main always calls invalidate_implement_note before materializing; a compose-time prepare copied from that pattern clears a consumable durable note on guidelines-assessment relaunch and can loop NEEDS_USER_INPUT forever or drop the note before PR compose
- **Proposed resolution**: Specify that compose-time prepare clears only staged and dropped-note artifacts, or short-circuits when note_consumable matches current HEAD; do not call invalidate_implement_note on relaunch after a successful compose write



### FINDING_12:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/implement/ship_merge.py:222-266
- **Concern**: In-driver Step 12 rebase only pins/invalidates; it never re-enters PR-body compose. Scenario: After MERGE_RESULT_MAIN_ADVANCED or phase14 rebase, HEAD moves but the plan only removes _pin_or_invalidate_guidelines_note unless ship_merge explicitly calls the shared compose-time gate; the PR body can keep a stale or dropped note while CI/merge continues
- **Proposed resolution**: Require ship_merge to invoke the same compose-time helper used before pr-create (including NEEDS_USER_INPUT exit when reassessment is required) and update PR body via ensure_pr before returning to ci-initial



### FINDING_13:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/tests/implement/test_ci_monitor.py:2182-2252
- **Concern**: ci_monitor tests still require the retired pre-push guidelines pin. Scenario: The plan removes ci_monitor's out-of-gate pin/invalidate path, but test_run_ci_fix_pending_retry_pins_guidelines_before_push still monkeypatches _pin_or_invalidate_guidelines_note and asserts the old callback order; CI will fail or the implementation will retain the retired path to satisfy the stale test.
- **Proposed resolution**: Add python/tests/implement/test_ci_monitor.py to the firm updates and rewrite this test to assert pending retry does not pin or invalidate guidelines outside the compose gate.



### FINDING_14:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/larch/implement/ship_resume.py:371-382
- **Concern**: Pre-PR guidelines-assessment resume still falls through to fresh/postbump. Scenario: After the first Step 8 compose gate exits with PHASE=guidelines-assessment and no PR_NUMBER, _resume_plan still returns _fresh_resume_plan whenever pr_number is None (lines 371-378 and 381-382), so the relaunch reruns postbump instead of resuming at pr-create with the durable compose note; the plan names this loop risk but does not pin the intercept
- **Proposed resolution**: Add an early branch when state PHASE=guidelines-assessment and no PR exists: emit a dedicated ResumePlan.start (for example guidelines-assessment), teach ship.py to skip postbump for that start while still running the compose gate and pr-create path, and add the pre-PR resume test called for in test_ship.py



### FINDING_15:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/core/architectural_guidelines.py:912-940
- **Concern**: [SCOPE-REDUCTION] Plan adds a parallel compose-time prepare CLI though prepare already materializes. Scenario: architectural-guidelines prepare already invalidates stale artifacts, reads ARCHITECTURAL_GUIDELINES.md, and materializes the implementation diff; adding a second compose-prepare verb duplicates that surface and expands cli.py dispatch/grep churn without a behavioral gap Repurpose or extend prepare_main for the Step 8 compose gate (adjust invalidation semantics for compose-time only) instead of introducing a parallel prepare verb; repurpose write-staged-assessment into the compose durable writer where possible ### 1. correctness — `python/larch/implement/ship_resume.py:371-382` The compose-time flow depends on pausing after the first `NEEDS_USER_INPUT`, having the orchestrator write the durable note, and relaunching `step-8-ship.sh` without another postbump. Today `_resume_plan` maps any missing `PR_NUMBER` to `_fresh_resume_plan`, which always re-enters the `resume.start == "fresh"` postbump block in `ship.py`. The plan’s failure-mode note flags that risk but does not require the concrete fix at the actual fall-through site. Without an early `PHASE=guidelines-assessment` branch and matching `ship.py` skip-postbump handling, the end-to-end compose-time path can loop or never reach PR creation with the authored note. ### 2. architecture — `python/larch/core/architectural_guidelines.py:912-940` `prepare_main` already performs invalidate → read → materialize-diff, which is exactly what the compose gate needs after postbump. Adding a second compose-prepare CLI verb repeats that logic and increases migration surface (dispatch table, harness ports, grep cleanup) without closing a gap the feature requires. Minimum-change is to extend the existing `architectural-guidelines prepare` path for compose-time use and fold the durable write into a repurposed compose-assessment writer rather than parallel verbs.
- **Proposed resolution**: 



### FINDING_16:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/tests/implement/test_ci_monitor.py:2171-2244
- **Concern**: Plan drops ci_monitor pre-push pin/invalidate behavior but omits the existing test that requires it. Scenario: After the planned ci_monitor change, test_run_ci_fix_pending_retry_pins_guidelines_before_push still expects a _pin_or_invalidate_guidelines_note callback before push, so CI either fails or the implementation keeps the retired out-of-gate lifecycle path to satisfy the test
- **Proposed resolution**: Add python/tests/implement/test_ci_monitor.py to the plan and testing command, replacing this assertion with the compose-time contract: no pre-push guidelines pin/invalidate callback, and the next Step 8 compose gate owns reassessment



