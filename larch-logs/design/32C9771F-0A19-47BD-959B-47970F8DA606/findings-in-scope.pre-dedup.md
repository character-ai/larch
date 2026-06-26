### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/test_progress_report.py:576-581
- **Concern**: Existing dispatch precedence test still asserts Ship-PR when Step 5 evidence is present. Scenario: After the branch reorder, this assertion will fail and the suite will not pass, so the fix cannot land
- **Proposed resolution**: Update this test to assert Step 5 wins when live round artifacts are present, or replace it with a ship-pr fallback case that omits Step 5 evidence



### FINDING_2:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_progress_report.py:568-581
- **Concern**: Plan adds a regression test for Step 5 beating stale ship-pr but does not update test_dispatch_precedence. Scenario: That test asserts ship-pr wins when both a Step 5 timing mark and ship-pr-state.sh exist; after reordering _render_implement it will fail CI and encode the bug the issue fixes
- **Proposed resolution**: Update or replace test_dispatch_precedence so it expects Step 5 output when round artifacts exist, and add a sibling case where ship-pr wins only when Step 5 cannot render



### FINDING_3:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/progress_report.py:1473-1485
- **Concern**: Ship-pr fallback placement is ambiguous relative to progress/done. Scenario: The UPDATED section says to move the ship-pr branch after the Step 5 block inside if not done_marker.exists(); nesting it there drops the current early ship-pr path for done runs that still have ship-pr-state.sh
- **Proposed resolution**: Place if ship_state.is_file(): return _render_ship_pr(tmpdir) after the entire not-done Step 5 inference block, then fall through to _render_generic only when ship-pr is absent



### FINDING_4:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/test_progress_report.py:568-581
- **Concern**: Plan omits updating test_dispatch_precedence which encodes the bug as expected behavior. Scenario: The reorder fix makes Step 5 win when both a Step 5 timing mark and stale ship-pr-state.sh exist; test_dispatch_precedence still asserts Ship-PR phase: checks so make py-test fails until manually fixed
- **Proposed resolution**: Revise the plan Testing strategy to require flipping test_dispatch_precedence expectations (or replacing it) so ship-pr wins only when Step 5 rendering returns empty



### FINDING_5:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/progress_report.py:1473-1485
- **Concern**: Done-marker preservation bullets misstate current and target behavior. Scenario: The plan says done runs with ship-pr-state should show ship-pr but _render_implement today and the proposed reorder both skip Step 5 and ship-pr when progress/done exists and fall through to generic; adding done-path ship-pr would break test_step5_done_falls_through and expand scope beyond issue 5464
- **Proposed resolution**: Clarify the plan that done runs keep the existing generic timing-ledger report only; place the ship-pr fallback strictly inside the not done_marker.exists() block after Step 5 inference fails



### FINDING_6:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/test_progress_report.py:568-581
- **Concern**: The existing `test_dispatch_precedence` still asserts Ship-PR wins when Step 5 and `ship-pr-state.sh` coexist.. Scenario: After the proposed `_render_implement` reorder, that assertion will fail in CI even if the new behavior is correct, so the PR cannot merge until the test is updated.
- **Proposed resolution**: Rewrite this test to assert live Step 5 output wins with a stale ship-pr state, and keep ship-pr-only coverage in the dedicated ship-pr tests.



