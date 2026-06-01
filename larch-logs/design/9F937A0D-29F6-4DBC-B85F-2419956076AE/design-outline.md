## Proposed Design Outline

### Goals
- Extract the Step 8+ OOS disposition-gate input plumbing (~95 inline bash lines in `skills/implement/SKILL.md`) into `skills/implement/scripts/oos-disposition-checkpoint.sh`.
- Helper resolves inputs, invokes `oos-disposition-gate.sh`, logs failures, and exits 0/1/2 so the orchestrator branches on the return code.
- Remove the determinism hazard of hand-hosted `merge-base` / `find` / `awk` / CSV plumbing.

### Non-goals
- No `ship-pr.sh` edits (separate block in the same mega-section).
- Helper does NOT clear `OOS_PENDING`, write `run-statistics`, or own `--resume-phase pr-create` — the orchestrator keeps those (NEVER #17 / #18).
- No change to `oos-disposition-gate.sh` semantics or its `--oos-issues-ndjson` / `--filed-urls-file` / `--filed-urls-strict-file` / `--commit-range` wiring.

### Approach sketch
- New `oos-disposition-checkpoint.sh --implement-tmpdir <dir> [--design-tmpdir <dir>]` ports the current inline logic (FORKED_TARGET/REPO_UNAVAILABLE read, commit-range, RUN_ID + ndjson discovery, design-OOS path, non-security block count, precondition, gate call).
- Exit contract mirrors the gate: 0 proceed, 1 disposition gap, 2 validation/setup (gate exit 2 plus the pre-gate input-resolution failures that already exit 2 today).
- Helper calls `append-tool-failure.sh` on ALL non-zero exits with distinct `--site` tokens.
- Replace the SKILL.md inline block with a thin helper call plus a documented 0/1/2 rc branch.

### Surfaces in scope
- `skills/implement/scripts/oos-disposition-checkpoint.sh` (new) + `oos-disposition-checkpoint.md` (new contract sibling).
- `skills/implement/SKILL.md` (replace inline block with helper call).
- `skills/implement/scripts/test-oos-disposition-gate.sh` (+ `.md`) — add checkpoint coverage.
- `scripts/test-implement-structure.sh` — update inline-block structural pins if present.

### Open questions
- None. Exit-code and failure-logging contracts were resolved in Step 1c.
