## Goal
Implement issue #6022: [IMPLEMENTING] [BUG] #5972 residual: collector cursor CMD_JSON retry lacks NO_OPEN_BROWSER=1.

## Implementation Plan
## Summary

#5972 / PR #5996 fixed the /design vendor auto-fix Cursor lane, but one Cursor spawn lane still lacks the export: `_launch_cmd_json_retry` in the collector process relaunches a cursor CMD_JSON via Popen with `_env_without_test_hooks()`, and `cursor_auth_export_env()` is never called inside the collector process, so a Cursor.app GUI popup can still fire from that lane.

## Original report

From the 2026-07-02 post-merge audit of #5972 / PR #5996 at 63ed17f18. The run's reviewer acknowledged this lane as OOS_3 (pre-existing, outside that PR's scope) and it was dropped before the vote; 0 OOS filed. Status: suspected residual popup lane, not confirmed end to end, because the lane is narrow (see Root cause analysis).

## Reproduction scenario

A collector-side CMD_JSON retry for a cursor invocation that is not rejected by the review-shape gate spawns `cursor agent` without NO_OPEN_BROWSER in a session where the operator has not exported it; if Cursor decides to open an auth or browser flow, the GUI popup fires during an otherwise headless run.

## Expected behavior

Every production Cursor spawn composes its environment through `agents.cursor_auth_export_env()` (which sets NO_OPEN_BROWSER=1 and normalizes CURSOR_API_KEY) before launch, matching all other lanes.

## Observed behavior

python/larch/review/collect_results.py:463-468: `Popen(env=_env_without_test_hooks())` with no cursor env export in-process. The export performed by `agent launch-review` happens in a sibling subprocess and does not reach the collector's environment.

## Root cause analysis

The audit swept all Cursor spawn-composition sites at 63ed17f18: every other production lane exports pre-spawn (python/larch/agents/_review_launcher.py:1119, _ci_launcher.py:334 and :794, _drafter.py:172, python/larch/review/coder_runner.py:214, python/larch/implement/checks_lint_fix.py:656, the _auth.py probe chain, and the research validation shell lane). The collector retry lane predates #5972 and was out of its plan scope. Exposure is narrow: review-shaped and `--mode ask` cursor retries are rejected at collect_results.py:437 and rerouted through the outer launcher.

## Evidence

- collect_results.py:463-468 (the Popen without export) and :437 (the reject-and-reroute gate), cited by the audit at 63ed17f18.
- Issue search for NO_OPEN_BROWSER returns only #5797 and #5972; no issue tracks this lane.

## Affected files

- python/larch/review/collect_results.py: `_launch_cmd_json_retry`.
- python/larch/agents/_auth.py: exported helper to reuse.
- The #5972 regression test file (python/tests/design/test_plan_quality.py) as a pattern for the new test.

## Suggested fix(es)

- Call `agents.cursor_auth_export_env()` (or pass an explicitly composed env) in `_launch_cmd_json_retry` when the retried command is a cursor invocation; add a test that captures the child env at the spawn point.
- Secondary hardening from the same run (OOS_6): the #5972 test asserts the env outcome rather than helper invocation, so a future inline `os.environ["NO_OPEN_BROWSER"] = "1"` refactor could keep the test green while dropping CURSOR_API_KEY normalization; consider asserting the full env contract (browser suppression plus key normalization) in one place.

## Open questions

- Is the collector cursor retry lane reachable for any current production CMD_JSON shape? If provably dead, delete the lane instead of patching it.

## Test plan
(no test plan section in plan-file)
