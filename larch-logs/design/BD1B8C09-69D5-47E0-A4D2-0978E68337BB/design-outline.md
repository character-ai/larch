## Proposed Design Outline

### Goals
- Add `implement commit-route` verb in Python that runs `commit-fixes`, gates on `COMMIT_OUTCOME`, seeds durable-bail state on failure, and emits `NEXT_ACTION=continue|stall`.
- Collapse the three SKILL.md commit-parse-and-stall prose blocks (Step 5 self-review, Step 5 resume-handoff, Step 7) to a single fence + one-line `NEXT_ACTION` branch.
- Provide pytest coverage for all site paths and failure modes.

### Non-goals
- Changes to the `commit-fixes` verb itself.
- Changes to `ship-pr-state.sh` key schema or `_ALLOWED_SHIP_STATE_KEYS`.
- Changes to stall classification, Step 18, or `stall-recovery` verbs.
- Refactoring other commit-related helpers beyond the three SKILL.md sites.

### Approach sketch
- Add `commit_route_main` in `python/implement_dispatch.py` behind `("implement", "commit-route")` in `cli.py`.
- Accept `--site` with values `step5-self-review`, `step5-resume-handoff`, `step7`; map site to `(stall_step, stall_reason, log_prefix)`.
- On commit failure: log to `execution-issues.md` via `run-log append-failure`, then seed or key-rewrite `ship-pr-state.sh`; emit `NEXT_ACTION=stall`.
- On commit success (`ok`/`noop`): relay `COMMITTED`, `SHA`, `ERROR` KVs and emit `NEXT_ACTION=continue`.
- Update `skills/implement/SKILL.md` to replace the three prose blocks with a single `commit-route --site <SITE>` fence and "branch on `NEXT_ACTION`".

### Surfaces in scope
- `python/implement_dispatch.py` (new verb)
- `python/cli.py` (new dispatch entry)
- `python/test_implement_dispatch.py` (new tests)
- `skills/implement/SKILL.md` (3 prose block replacements)

### Open questions
- None.
