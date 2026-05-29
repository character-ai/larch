## Proposed Design Outline

### Goals
- Make `write-design-current-env.sh` preserve the four reviewer presence/availability keys across a no-flag refresh.
- Stop the Step 3 launch failure where empty `--codex-present` / `--cursor-present` trip `plan-review-loop.sh`'s `${2:?}` guard.

### Non-goals
- No edits to SKILL.md refresh callsites or the Step 3 / Step 3.6 consumer blocks.
- No change to `MANUAL_REQUESTED` clear-on-omit semantics (test Case 12 stays green).
- No consumer-side defensive defaults (backstop declined in Round 1).

### Approach sketch
- On every write, recover prior values of the four keys from the existing `--output` file when the matching flag is omitted.
- Emit each of the four keys when the flag was passed OR a prior value was recovered.
- Leave `MANUAL_REQUESTED`, `REPO`, `ISSUE_NUMBER` write-or-omit logic untouched; merge is scoped to the four presence/availability keys.

### Surfaces in scope
- `scripts/write-design-current-env.sh`
- `scripts/write-design-current-env.md`
- `skills/design/scripts/test-write-design-current-env.sh`

### Open questions
- None.
