## Goal
Prevent scout parse-failed warnings from leaking into parent /implement run execution-issues when test fixtures fire

## Implementation Plan

Add test-tmpdir path guard to dispatch-panel.sh to prevent scout parse-failed
warnings from leaking into parent /implement run execution-issues.md.

Part A — dispatch-panel.sh:
- Add is_harness_scout_path() and should_suppress_scout_parse_issue_append()
- Modify append_scout_parse_issue(): add diag sidecar write, add path guard

Part B — test-dispatch-panel.sh:
- Apply env isolation to reuse-manifest-no-status and reuse-invalid-manifest tests
- Add 3 new regression tests (env-isolation, path-guard, prod-shape)

Also update dispatch-panel.md documentation.

## Test plan
(no test plan section in plan-file)
