### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/tests/design/test_design_lifecycle.py
- **Concern**: Test 1 must pin ambient REPO empty before asserting resolve_repo output. Scenario: _load_wrapper_env seeds REPO from os.environ via _base_env before source-env overlay. Planned Test 1 omits source-env REPO but still expects _read_json_issue and design route to use resolve_repo's new/repo. When os.environ.REPO is non-empty, the ISSUE_NUMBER-only guard correctly skips gap-fill and preserves ambient REPO, so resolve_repo is never called; assertions on new/repo false-fail on fixed code, and the stale-route-state leak may not be exercised when ambient REPO masks the old OR guard.
- **Proposed resolution**: In Test 1 add monkeypatch.delenv("REPO", raising=False) or monkeypatch.setenv("REPO", "") before step0_route_main, matching the empty-REPO precondition in the plan's failure-modes section and the ambient-REPO isolation pattern used elsewhere (e.g. test_plan_quality.py).



### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: plan.txt:36-42
- **Concern**: Test 2 does not stub the `proc.run` call used by `_refresh_resume_source_env`.. Scenario: If the route fake returns a `resume@...` result, the test will invoke the real `session write-design-env` command instead of staying isolated, so it can mutate the session env or fail for host-environment reasons before proving the ISSUE_NUMBER recovery.
- **Proposed resolution**: Add the same `design_step0.proc.run` monkeypatch used by the nearby resume tests, and keep the fake route result on the resume path.



