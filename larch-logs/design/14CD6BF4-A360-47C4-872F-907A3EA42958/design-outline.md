## Proposed Design Outline

### Goals
- Add auth classification to the Step-7a code-flow diagram lane so degraded-auth timeouts surface as `health/auth` instead of a generic `generation-failed rc=124 tail=` reason.
- Reduce the hard-coded 600s timeout to 180s for this best-effort lane.

### Non-goals
- Do not add a dedicated Claude auth preflight function (the existing `_run_claude_with_stdin` fast-fail already handles auth within ~60s; `external_auth_verdict` post-failure classification is sufficient).
- Do not change `launch_claude_subprocess_main` in `agents.py`; all changes stay in `pr_body.py`.
- Do not change how step_7a.py consumes the reason string (other than it now gets `health/auth`).

### Approach sketch
- Import `external_auth_verdict` from `larch.agents.agents` into `pr_body.py` (no circular dependency).
- In `generate_code_flow_diagram`, change `--timeout` from `"600"` to `"180"`.
- After `completed.returncode != 0`, read the `.stderr` sidecar written by `launch_claude_subprocess_main` and call `external_auth_verdict("claude", sidecar)`.
- If verdict is `"auth"`, set `reason = "generation-failed health/auth"` and skip `_diagram_failure_capture`; otherwise use the existing failure path.
- Add a test in `test_pr_body.py` that simulates an auth timeout (rc=124, sidecar with degraded-auth message) and asserts `reason == "generation-failed health/auth"`.

### Surfaces in scope
- `python/larch/git/pr_body.py` (single function `generate_code_flow_diagram`)
- `python/test_pr_body.py` (one new test)

### Open questions
- None.
