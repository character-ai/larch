## Proposed Design Outline

### Goals
- Fix `_review_launch_codex` to use the consumer git-repo root as `workdir`, not `Path.cwd()` (which is overridden to the plugin root by `run_legacy_script`).
- Belt-and-suspenders: fix `_run_external_agent_with_auth_retries` to retry on "unclassified" (all-empty-sidecar) exit-1 failures, not only explicit auth failures.

### Non-goals
- Do not change `run_legacy_script`'s `cwd=str(_REPO_ROOT)` — that override is intentional for script lookup.
- Do not add `--workdir` to `agent launch-review` (Option B from the issue); Option A resolves the root cause without a new public flag.
- Do not change Cursor's `--workspace str(Path.cwd())` path; Cursor does not perform a git-repo check.

### Approach sketch
- Add `_resolve_consumer_repo_root(cwd: str) -> str` to `python/agents.py`: runs `git -C <cwd> rev-parse --show-toplevel`, falls back to `cwd` on failure.
- In `_review_launch_codex` at line 3540, replace `workdir = str(Path.cwd())` with `workdir = _resolve_consumer_repo_root(str(Path.cwd()))`.
- In `_run_external_agent_with_auth_retries` at line 2182, allow retry when `external_auth_verdict` returns `"unclassified"` (no readable sidecars) on a non-zero exit.

### Surfaces in scope
- `python/agents.py` (two edits: new helper + workdir fix + auth-retry fix)
- `python/test_launch_review.py` (new test: workdir resolves to git root, not raw cwd)
- `python/test_agents.py` (new test: auth-retry allows one retry on "unclassified" verdict)

### Open questions
- None.
