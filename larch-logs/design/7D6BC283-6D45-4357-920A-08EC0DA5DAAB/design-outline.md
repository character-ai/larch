## Proposed Design Outline

### Goals
- Audit each unguarded helper called in `phase_plan_materialize` (lines ~750-911) and confirm idempotency on `--resume-plan-tail` re-entry.
- Add or extend structural test pins so SKILL.md Step 0 dirty-tree recovery contract stays in sync with `implement-bootstrap.sh`.

### Non-goals
- Any behavior change to `phase_tracking` or `phase_plan_materialize` (logic edits, new guards, refactors).
- New mechanical bootstrap harness cases in `test-implement-bootstrap.sh`.
- Rework of the dirty-tree recovery flow itself.

### Approach sketch
- For each helper in `phase_plan_materialize` lines ~750-911 (dirty-tree checkpoint, branch derivation, run-plan log, plan-review tally, larch:plan summary upsert), state in the plan whether it is idempotent on resume and why (marker upsert, branch already-exists short-circuit, tmpdir-local file write, etc.).
- Surface findings in `scripts/implement-bootstrap.md` under a small "Resume-tail idempotency" section so future readers see the same evidence the audit gathered.
- Identify which lines in `scripts/test-implement-structure.sh` (419-444 area) already cover the dirty-tree recovery surface; add only the assertions missing from that surface.

### Surfaces in scope
- `scripts/implement-bootstrap.md` — documentation-only audit section.
- `scripts/test-implement-structure.sh` — new structural assertion(s) only if a gap remains.
- `scripts/implement-bootstrap.sh` — inline comments only if the audit reveals a non-obvious invariant; no logic edits.

### Open questions
- None.
