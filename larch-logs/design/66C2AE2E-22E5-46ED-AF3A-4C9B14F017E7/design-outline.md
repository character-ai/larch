## Proposed Design Outline

### Goals
- Migrate all 7 bash skill-structure harnesses (alias, bug, design, implement, learn-from-bugs, research, review) to a single parameterized pytest suite with full parity.
- Provide a `SkillPin` dataclass + per-skill pin tables covering `contains`, `absent`, `exact-count`, `ordered`, and `same-line` predicates; keep CLI-backed and executable-bit checks as named tests.
- Delete all 7 `.sh` harnesses (plus 6 `.md` companions) after parity; update Make targets, shard entries, residual-bash-paths.txt, and docs/linting.md.

### Non-goals
- No new assertion logic beyond what the 7 Bash harnesses already cover.
- No changes to pytest sharding or CI shard counts.
- No changes to the 7 skills' SKILL.md content.

### Approach sketch
- Add `python/tests/skills/__init__.py`, `python/tests/skills/skill_structure_pins.py` (SkillPin dataclass + 7 per-skill pin tables), and `python/tests/skills/test_skill_structure.py` (parametrized dispatch + named tests for complex checks).
- Each Make target (`test-alias-structure`, etc.) changes from `bash scripts/...` to `python3 -m pytest python/tests/skills/test_skill_structure.py -k <skill> -q`.
- Remove 7 entries from `scripts/residual-bash-paths.txt`.
- Update 4 entries in `docs/linting.md` that reference the bash scripts.

### Surfaces in scope
- `python/tests/skills/` (new directory with 3 files)
- `scripts/test-alias-structure.sh`, `test-bug-structure.sh`, `test-design-structure.sh`, `test-implement-structure.sh`, `test-learn-from-bugs-structure.sh`, `test-research-structure.sh`, `test-review-structure.sh` (delete)
- `scripts/test-alias-structure.md`, `test-bug-structure.md`, `test-design-structure.md`, `test-implement-structure.md`, `test-research-structure.md`, `test-review-structure.md` (delete)
- `Makefile` (7 target bodies)
- `scripts/residual-bash-paths.txt` (7 removals)
- `docs/linting.md` (4 table rows)

### Open questions
- None.
