## Proposed Design Outline

### Goals
- Compute `SETTLE_NEXT_ACTION` (settle-rc) and a new step2b5 action key in Python, not Bash or orchestrator prose.
- Shrink `settle-rc-dispatch.md` and `step2b5-rc-handling.md` to branch bodies; keep prose only for genuinely UI-facing text (prompts, print formats).
- Preserve exact current routing: every existing rc/site and trigger-boolean combination routes the same way as today.

### Non-goals
- No routing semantics change on any existing combination.
- No new `/design` flags, gates, or features.
- Do not port all of `design-step35-settle.sh` (pause handling, dedup, postplan call) to Python; only the pure dispatch decision moves.

### Approach sketch
- Move the settle rc x site dispatch (`design_settle_next_action_for_rc` in `design-step35-settle.sh`) into a Python helper behind `cli.py`; the Bash script calls it instead of its own `case` statement.
- Add an equivalent Python-computed action key for the step2b5 hard/partition/drift/no-trigger choice, extending `python/cli.py design step2b5`.
- Add pytest fixtures covering the full existing dispatch matrix for both, to prove parity.
- Update the two reference docs, their SKILL.md/approval-gates.md/discussion-rounds.md call sites, and `scripts/test-design-structure.sh` pins together.

### Surfaces in scope
- `skills/design/scripts/design-step35-settle.sh`
- `skills/design/references/settle-rc-dispatch.md`, `step2b5-rc-handling.md`
- `python/larch/design/design_lifecycle.py`, `python/larch/cli.py`
- `skills/design/SKILL.md`, `approval-gates.md`, `discussion-rounds.md` (call-site prose only)
- `scripts/test-design-structure.sh`
- New/updated tests under `python/tests/design/`

### Open questions
- None.
