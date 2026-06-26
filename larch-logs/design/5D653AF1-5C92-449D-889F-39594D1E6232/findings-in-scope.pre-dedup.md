### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/test_external_dispatch.py:70-70
- **Concern**: [SCOPE-REDUCTION] Consumer matrix still targets ci_monitor._available_tiers even though it has no production call sites.. Scenario: _available_tiers is reportUnusedFunction at python/ci_monitor.py:1279-1280. Live CI recovery hardcodes tier=claude in python/ci_agentic_fix.py:492-494. A new probe only re-tests dead code and cannot catch registry drift at a real dispatch boundary.
- **Proposed resolution**: Drop ci_monitor._available_tiers from the planned consumer list. Keep rebase, bootstrap, review, plan-scout, and decompose probes that hit live call sites.



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: python/test_external_dispatch.py:72-72
- **Concern**: [SCOPE-REDUCTION] scout_plan_archetypes role-id forwarding is already covered in python/test_plan_scout.py:544-565.. Scenario: Adding the same boundary probe to test_external_dispatch.py inflates diff (~324 planned lines) without new drift signal; a registry-only regression can still pass both files.
- **Proposed resolution**: Omit scout_plan_archetypes from test_external_dispatch.py. Keep scout_dynamic_archetypes and plan_review_panel entries that exercise distinct runtime paths.



### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:63-77
- **Concern**: Runtime-dispatch test matrix omits two live consumers from the promised per-consumer coverage. Scenario: The proposed `python/test_external_dispatch.py` list still leaves `design_lifecycle.step2b_drafter_main` (`design.plan_drafter`) and `plan_quality.revise_plan_with_waterfall_main` (`design.plan_revision`) untested at the consumer boundary, so drift in either role can still pass CI
- **Proposed resolution**: וסיף Add boundary probes for those two module entrypoints in the new test file, or explicitly move them into separate runtime-dispatch tests if you want to keep the matrix split



### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_implement_dispatch.py:46-53
- **Concern**: Composite skip integration tests only name `_run_leg_with_timeout`; they omit required mocks for commit/resume (and 7.r when used). Scenario: After a mocked skip envelope, `checks_commit_route_main` still calls `_run_commit_route_leg` and optional `_run_7r_rebase_checkpoint`; `checks_step5_resume_main` calls `_run_step5_resume_leg`. Existing composite tests (e.g. `test_composite_rebase_checkpoint_skips_checks_failed` at 1691-1716) mock those legs explicitly. A literal follow of the plan exercises real subprocess commit/resume/7.r paths and flakes or fails offline.
- **Proposed resolution**: Add to the plan: mock `_run_commit_route_leg` (and `_run_7r_rebase_checkpoint` when argv includes `--rebase-checkpoint-7r`) for `checks_commit_route_main` skip tests; mock `_run_step5_resume_leg` for `checks_step5_resume_main`. Prefer `step5-self-review` without `--rebase-checkpoint-7r` for the minimal skip path, matching existing `_mock_composite_continue` patterns.



### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: python/test_external_dispatch.py:72
- **Concern**: [SCOPE-REDUCTION] `plan_scout.scout_plan_archetypes` role-id forwarding is already covered by `python/test_plan_scout.py::test_plan_wrapper_forwards_role_id_to_inner_override` (544-577). Scenario: Adding the same probe to the new matrix inflates diff without new drift signal; issue item 3 needs runtime dispatch boundaries, not a second copy of an existing consumer test.
- **Proposed resolution**: Drop the `scout_plan_archetypes` row from the consumer list; keep `scout_dynamic_archetypes` and other consumers that lack boundary probes.



### FINDING_6:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:61-77; python/design_lifecycle.py:3632-3636; python/plan_quality.py:1658-1666
- **Concern**: Current external-dispatch matrix still omits live consumers `design.plan_drafter` and `design.plan_revision`.. Scenario: Registry-level coverage can pass while the plan drafter or plan revision order drifts at runtime, so the item-3 test matrix still leaves two real dispatch paths unguarded.
- **Proposed resolution**: Add boundary probes for those two sites, either in `python/test_external_dispatch.py` or in their existing native test files, so every live external-default consumer has a runtime assertion.



### FINDING_7:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/test_implement_dispatch.py:56-59
- **Concern**: Item 2 triple-surface sync leaves the Step 6 SKILL timeout literal cross-pin optional even though structure-harness cross-pin is required. Scenario: Round-1 accepted FINDING_2 required SKILL and harness literals stay aligned with CHECKS_COMMIT_ROUTE_OUTER_TIMEOUT_MS. Structure-only pytest can pass while skills/implement/SKILL.md:677 still says timeout: 14700000, so folded 7.r keeps the latent outer kill the issue targets
- **Proposed resolution**: Make the Step 6 SKILL fence literal assertion mandatory (same as the structure harness cross-pin), not optional



### FINDING_8:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/shared/voting-protocol.md:66-71
- **Concern**: Item 4 doc fix does not explicitly require correcting the false code-review composition claim that Codex availability never changes voter makeup. Scenario: Post-#5311 voters 2-3 are Codex-primary (python/agent_voters.py:76-77). Leaving line 71 unchanged after slot-label edits still tells operators Codex does not affect composition, failing item 4 acceptance
- **Proposed resolution**: Add an explicit plan step to rewrite the code-review paragraph at lines 66-71 (and matching Overview/degraded-panel/Launching Voters sentences) so v2/v3 Codex participation and waterfall behavior are stated, not only the v1/v2/v3 label tokens



### FINDING_9:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/test_external_dispatch.py:70
- **Concern**: [SCOPE-REDUCTION] Consumer matrix still probes ci_monitor._available_tiers despite no production dispatch site. Scenario: Item 3 asks for tests at actual runtime dispatch boundaries. _available_tiers is reportUnusedFunction (python/ci_monitor.py:1279-1280); CI recovery is Claude-only today (python/ci_agentic_fix.py). A new probe only re-tests dead code and duplicates python/test_ci_monitor.py:90-91
- **Proposed resolution**: Drop ci_monitor._available_tiers from the planned consumer list; keep the live consumers already named in the plan



