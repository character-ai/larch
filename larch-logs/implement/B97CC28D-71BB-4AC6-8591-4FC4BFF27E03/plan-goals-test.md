## Goal
Implement issue #5674: [IMPLEMENTING] [BUG] Step-7a code-flow diagram lane times out (exit 124) with no fast-fail.

## Implementation Plan
## Plan

## Context

- `approach-synthesis.txt` was `NO_SKETCHES`.
- No planning-panel consensus is assumed.
- The current shared Claude runner already contains degraded-auth fast-fail logic.
- The code-flow lane does not surface that classification clearly to Step 7a.

## Approach

1. Keep the fast-fail behavior in the shared Claude runner.
2. Make `agent launch-claude-subprocess` emit launcher failure class fields, matching the CI and lint-fix lanes:
   - `LAUNCHER_FAILURE_CLASS=health`
   - `LAUNCHER_FAILURE_REASON=auth`
3. Have `generate_code_flow_diagram` parse those fields from launcher stdout.
4. Include the classification in the Step-7a warning reason.
5. Replace the hard-coded `600` timeout with a module constant for this best-effort lane.
6. Lower the code-flow timeout to a shorter cap, such as `180`, so non-auth hangs no longer burn 10 minutes.
7. Keep the lane non-fatal.

## Files to modify/create

### UPDATED: python/larch/agents/agents.py

Add a small helper for `launch_claude_subprocess_main` that classifies and emits launcher failure fields.

Implementation notes:

- Reuse existing helpers:
  - `external_auth_verdict("claude", ...)`
  - `classify_launch_failure(...)`
- Feed it the output sidecars already written by this launcher:
  - `output.with_suffix(output.suffix + ".stderr")`
  - `output.with_suffix(output.suffix + ".stderr-tail")`
  - `output.with_suffix(output.suffix + ".failure-diag")`
  - `output`
- Emit:
  - `LAUNCHER_FAILURE_CLASS`
  - `LAUNCHER_FAILURE_REASON`
- Preserve existing stdout keys:
  - `STATUS`
  - `OUTPUT_FILE`
  - `ELAPSED`
- Do not change the launcher return code.
- Do not add another polling loop. `_run_claude_with_stdin` owns timeout and fast-fail behavior.

### UPDATED: python/larch/git/pr_body.py

Update `generate_code_flow_diagram`.

Implementation notes:

- Add a module-private timeout constant near other diagram constants:
  - `_CODE_FLOW_DIAGRAM_TIMEOUT_SECONDS = 180`
- Use the constant instead of the hard-coded `"600"`.
- Add a small parser for launcher stdout KV lines.
- On non-zero launcher exit:
  - Parse `LAUNCHER_FAILURE_CLASS`.
  - Parse `LAUNCHER_FAILURE_REASON`.
  - If both are present and non-empty, append a stable label such as `health/auth` to the generated reason.
- Keep the existing sanitized tail and bounded failure log behavior.
- Preserve existing return shape:
  - `(1, "failed", "", reason)`
- Example target reason:
  - `generation-failed health/auth rc=124 tail=...`
- If classification is absent, keep the current generic reason shape.

### UPDATED: python/test_agents.py

Add focused launcher tests.

Coverage:

- Fake `claude` emits degraded-auth stderr and hangs.
- `launch_claude_subprocess_main` exits with `EXIT_TIMEOUT`.
- The elapsed time is below the requested timeout.
- The launcher writes the usual sidecars.
- stdout includes:
  - `STATUS=TIMEOUT`
  - `LAUNCHER_FAILURE_CLASS=health`
  - `LAUNCHER_FAILURE_REASON=auth`
- Keep existing missing-binary and bad-json tests compatible with the new extra stdout fields.

### UPDATED: python/test_pr_body.py

Update and add code-flow tests.

Coverage:

- The launch argv uses `_CODE_FLOW_DIAGRAM_TIMEOUT_SECONDS`, not literal `600`.
- A fake launcher stdout containing `LAUNCHER_FAILURE_CLASS=health` and `LAUNCHER_FAILURE_REASON=auth` produces a reason containing `health/auth`.
- Existing redaction assertions still hold.
- Existing failure-log assertions still hold.
- Update stale fixture text that says `timeout after 600s` only where the test is asserting the new timeout behavior.

## Edge cases

- If launcher stdout is empty, keep the existing generic timeout reason.
- If auth appears only in stderr sidecars, the launcher should still classify it before `pr_body.py` parses stdout.
- If the launcher exits `124` for a true non-auth timeout, classify it as timeout, not auth.
- If failure-log writing fails, preserve the existing `log-write-failed` suffix behavior.
- Do not include raw Mermaid output or secrets in warnings or logs.

## Failure modes

- A shorter timeout may skip a slow but valid diagram.
  - This is acceptable because the lane is best-effort and currently drops diagrams after burning much longer.
- Classification can be absent if an older test launcher is injected.
  - Keep backward-compatible generic reasons.
- Degraded-auth signatures may change.
  - This plan reuses the existing regex instead of adding a second copy.

## Testing strategy

Run targeted tests:

- `python3 -m pytest python/test_agents.py -k 'launch_claude_subprocess'`
- `python3 -m pytest python/test_pr_body.py -k 'generate_code_flow_diagram'`
- `python3 -m pytest python/test_step_7a.py -k 'diagram_failure'`

Then run changed-file lint if available in the local workflow:

- `python3 -m ruff check python/larch/agents/agents.py python/larch/git/pr_body.py python/test_agents.py python/test_pr_body.py python/test_step_7a.py`

## Acceptance

Run targeted tests:

- `python3 -m pytest python/test_agents.py -k 'launch_claude_subprocess'`
- `python3 -m pytest python/test_pr_body.py -k 'generate_code_flow_diagram'`
- `python3 -m pytest python/test_step_7a.py -k 'diagram_failure'`

Then run changed-file lint if available in the local workflow:

- `python3 -m ruff check python/larch/agents/agents.py python/larch/git/pr_body.py python/test_agents.py python/test_pr_body.py python/test_step_7a.py`

diff_added: 115
diff_deleted: 20
mechanical_churn: false
diff_lines: 135

## Test plan
(no test plan section in plan-file)
