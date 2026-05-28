## Proposed Design Outline

### Goals
- Add fixed-string CI lint that catches stale Gate B prose before merge.
- Add automated coverage for the SKILL.md Step 0b jq-merge recovery (FINDING_8/9).
- Extend `scripts/test-write-run-params.sh` with `--manual-gate-b` failure-path coverage.

### Non-goals
- Edit `SECURITY.md`, `docs/issue-anchored-plan.md`, or other surfaces to add new cross-references (Decision 1: surfaces already aligned).
- Refactor the Gate B mode-resolution precedence in `approval-gates.md`.
- Change the `scripts/write-run-params.sh` interface or behavior.

### Approach sketch
- In `scripts/test-design-structure.sh`, add `absent` checks for stale Gate B phrases against approval-gates.md, SKILL.md, docs/workflow-lifecycle.md, and docs/configuration-and-permissions.md.
- In `scripts/test-write-run-params.sh`, add failure-path cases: missing `--manual-gate-b` value and `--manual-gate-b` enum violations.
- Create `scripts/test-step0b-router-flag-recovery.sh` that runs the SKILL.md Step 0b shell snippet, asserts OR-merge for partition/brainstorm and overwrite-semantic for manual_gate_b.
- Register the new harness as a Makefile target alongside `test-write-run-params`.

### Surfaces in scope
- `scripts/test-design-structure.sh`
- `scripts/test-write-run-params.sh`
- `scripts/test-step0b-router-flag-recovery.sh` (NEW) + sibling `.md` per script-md-siblings rule.
- `Makefile`

### Open questions
- None.
