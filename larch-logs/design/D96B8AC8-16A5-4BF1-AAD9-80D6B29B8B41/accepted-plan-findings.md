### FINDING_1: Pin ambient REPO for Test 1
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Concern**: Test 1 can pass or fail for the wrong reason because it assumes `resolve_repo()` runs even when `os.environ.REPO` is already populated. That leaves the ambient repo state unpinned and can mask the stale-route-state path the test is meant to cover.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In Test 1 add monkeypatch.delenv("REPO", raising=False) or monkeypatch.setenv("REPO", "") before step0_route_main, matching the empty-REPO precondition in the plan's failure-modes section and the ambient-REPO isolation pattern used elsewhere (e.g. test_plan_quality.py).


