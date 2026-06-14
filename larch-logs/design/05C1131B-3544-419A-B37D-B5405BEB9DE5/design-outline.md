## Proposed Design Outline

### Goals
- Add `python/cli.py agent launch-review` as the Python port of `scripts/launch-review.sh` (Codex + Cursor review launcher).
- Retarget all live callers (`dispatch-with-waterfall.sh`, `collect-agent-results.sh` retry path) to the new verb.
- Retire `scripts/launch-review.sh`, its `.md` contract, and test harnesses; add pytest parity.

### Non-goals
- Full migration of `collect-agent-results.sh` or `dispatch-with-waterfall.sh` (only the `launch-review.sh` call sites are retargeted).
- Changes to `dispatch-plan-voters.sh` (only a comment reference, not a direct caller).
- New launcher features beyond bash parity.

### Approach sketch
- Implement `launch_review_main` in `python/agents.py`; register `("agent", "launch-review")` in `cli.py`.
- Accept `--tool codex|cursor` plus all existing flags; dispatch to per-tool private helpers.
- Preserve `LARCH_PROMPT_SENTINEL=1` compact hash sentinel for `--agent-file` retries.
- Replace `snapshot-untracked.sh` calls with `python3 cli.py dirty-tree checkpoint`.
- Reuse existing Python auth, serial-lock, `_run_external_agent_with_auth_retries`, timing, and token-recording helpers.

### Surfaces in scope
- `python/agents.py` (new `launch_review_main` + private helpers)
- `python/cli.py` (registry entry)
- `python/test_agents.py` or new `python/test_launch_review.py` (pytest)
- `scripts/dispatch-with-waterfall.sh` (retarget codex/cursor launch calls)
- `scripts/collect-agent-results.sh` (retarget `launch-review.sh` OUTER_LAUNCHER check)
- `scripts/launch-review.sh`, `scripts/launch-review.md`, `scripts/test-launch-review.sh`, `scripts/test-launch-review.md` (delete)
- `python/migrated-scripts.tsv` (append)
- `docs/external-reviewers.md`, `docs/configuration-and-permissions.md`, `docs/linting.md` (reference updates)
- `scripts/lib-codex-launcher-common.md`, `scripts/lib-cursor-launcher-common.md` (edit-in-sync update)

### Open questions
- None.
