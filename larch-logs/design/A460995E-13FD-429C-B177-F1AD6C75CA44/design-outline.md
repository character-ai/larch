## Proposed Design Outline

### Goals
- Record every residual proposal from a learn-from-bugs run in the durable state marker (schema v2).
- Check whether prior proposals landed before each new run and surface the results in the report.
- Suppress re-proposing of still-pending items by matching new proposals against prior pending ones by ID.

### Non-goals
- No automatic re-filing or reminder scheduling.
- No changes to what may be proposed (sibling #6968 owns proposal content requirements).
- No adoption enforcement; the check is observational only.

### Approach sketch
- Extend `LearnFromBugsState` / `_state_from_json` / `write_state` for v2 with a `proposals` list; v1 reads as v2 with empty proposals.
- Add `check_proposals(runner, proposals, root)` function and a new `check-proposals` CLI verb that verifies each prior proposal's status via file-system checks and `gh issue view`.
- Extend `write-state` CLI with a `--proposals-file` flag accepting a JSONL path.
- Update `read-state` CLI to emit proposal summary counts.
- Update SKILL.md: new adoption check step (Step 2.5), "Adoption since last runs" report section, dedup guidance, and schema v2 docs.

### Surfaces in scope
- `python/larch/issue/learn_from_bugs.py`
- `python/tests/issue/test_learn_from_bugs.py`
- `python/larch/cli.py`
- `skills/learn-from-bugs/SKILL.md`

### Open questions
- None.
