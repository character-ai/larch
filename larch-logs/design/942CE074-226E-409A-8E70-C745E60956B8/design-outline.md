## Proposed Design Outline

### Goals
- Make `--partition-requested` and `--brainstorm-requested` reject missing/empty values exactly like `--manual-gate-b` (`exit 2` + `larch_err` message).
- Remove the parsing asymmetry so callers can test `rc==2` and one stderr substring uniformly across all three boolean flags.

### Non-goals
- No change to `--reason`/`--source`/`--sketch-budget`/`--review-budget`/`--workflow-path`, which intentionally allow empty values (→ null).
- No change to valid-value handling or enum rejection (`maybe` still exits 2).
- No edits to other scripts that use `${2:?...}`.

### Approach sketch
- Add one shared `require_value` helper near `take_value` in `write-run-params.sh`.
- Route all three boolean flags through it (replaces the two `${2:?...}` lines and folds in `--manual-gate-b`).
- Call the helper directly, never inside `$(...)`, so `exit 2` propagates to the script.

### Surfaces in scope
- `scripts/write-run-params.sh` — argv parsing for the three boolean flags.
- `scripts/test-write-run-params.sh` — add symmetric `empty` + `missing` negative tests for both sibling flags.
- `scripts/write-run-params.md` — sync only if it documents per-flag rejection.

### Open questions
- None.
