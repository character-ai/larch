### OOS_1: Keep the step3 wait timeout import on the plugin path
- **Reviewer(s)**: Codex-Arch, Codex-Pragmatic
- **Severity**: important
- **Concern**: The shell launcher computes the timeout through inline Python, but that import path is not guaranteed in consumer repos, so Step 3 can fail before it writes the marker.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: `Specify the shell derivation as `PYTHONPATH="$CLAUDE_PLUGIN_ROOT/python"` or an inline `sys.path.insert(0, "$CLAUDE_PLUGIN_ROOT/python")` before importing `CHECKS_STEP3_BG_WAIT_TIMEOUT_S`, then keep the numeric validation/fail-closed check`
  - From Codex-Pragmatic: `Use a small CLI getter, or set PYTHONPATH to $CLAUDE_PLUGIN_ROOT/python or insert that path in the inline Python before importing the constant`


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### OOS_2: Write PHASE=rebase and fail closed on conflict handoff
- **Reviewer(s)**: Codex-Arch, Cursor-Pragmatic, Cursor-dyn-Ship Guard Auditor
- **Severity**: important
- **Concern**: The in-progress conflict branch should write durable rebase state and keep handoff write failures fail-closed; otherwise the user sees a traceback or incomplete state instead of a clean conflict-fix exit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: `Wrap every `_ship_pre_fix_patch_handoff` call site (including in-progress conflict routing) so OSError/ShipError returns through `_ship_pre_fix_fail` without emitting `NEXT_ACTION=``
  - From Cursor-Pragmatic: `Wrap every `_ship_pre_fix_patch_handoff` call site (including in-progress conflict routing) so OSError/ShipError returns through `_ship_pre_fix_fail` without emitting `NEXT_ACTION=``
  - From Cursor-dyn-Ship Guard Auditor: `Plan step is right but should be explicit: replace `_patch_ship_state_keys` with `_ship_pre_fix_write_conflict_state`, then patch handoff inside the same fail-closed envelope as `_ship_pre_fix_handle_conflict`; extend the in-progress regression to assert `PHASE=rebase` in `ship-pr-state.sh`.`


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### OOS_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/implement/dispatch_ship.py
- **Concern**: [SCOPE-REDUCTION] Freshness sentinel is written with no reader. Scenario: Binding item 1 also requires fail-closed ci-fix when PRE_FIX_REBASE_REQUIRED=true and the sentinel is absent; the plan only writes .ship-pre-fix-rebase-ok while SKILL.md already invokes ship pre-fix-rebase synchronously on every ci-fix/reship entry, so the marker is dead state unless a consumer and invalidation contract are added
- **Proposed resolution**: Either drop the sentinel writer from the plan, or add the consumer (check before ci-fix edits), unlink the sentinel when route-exit sets PRE_FIX_REBASE_REQUIRED, and test stale-sentinel refusal


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### OOS_4: Plan pins `assert "TIMEOUT_S=10800\n"` after deduplicating timeouts
- **Description**: Plan pins `assert "TIMEOUT_S=10800\n"` after deduplicating timeouts. Scenario: After constants land, a literal assertion reintroduces the same drift class the dedup work removes
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: python/tests/implement/test_implement_dispatch.py:102-126
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_5: phase14 reship still forces redundant pre-fix-rebase
- **Description**: phase14 reship still forces redundant pre-fix-rebase. Scenario: _ship_route_phase14_reship_pending already selects NEXT_ACTION=reship and still writes PRE_FIX_REBASE_REQUIRED=true, so the orchestrator always shells out to ship pre-fix-rebase even though the hardened path will immediately skip via the phase14 flag
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/larch/implement/dispatch_ship.py:322-323
- **Phase**: design

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_6: Normative exit-matrix docs omit the new sentinel gate
- **Description**: Normative exit-matrix docs omit the new sentinel gate. Scenario: SKILL.md will gate ci-fix/reship, but ship-pr-exit-matrix.md and ship-pr-ci-fix.md still say NEXT_ACTION=continue alone authorizes repair
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/implement/references/ship-pr-exit-matrix.md:37-39
- **Phase**: design




Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral

### OOS_7: Shell timeout dedup has no dedicated regression test
- **Description**: Shell timeout dedup has no dedicated regression test. Scenario: The plan adds a Python TIMEOUT_S assert in test_run_step_checks_main but does not exercise run-step-checks.sh, so a broken inline Python one-liner could desync the live shell marker
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/implement/scripts/run-step-checks.sh:76
- **Phase**: design

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected
