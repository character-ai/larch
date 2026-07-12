## Decision 1: Scope — exactly 7 skills, no others
- **Question**: Does the scope include any skills beyond alias, bug, design, implement, learn-from-bugs, research, review?
- **Resolution**: No. The issue explicitly lists exactly these 7 structure harnesses.
- **Source**: codebase (confirmed by grep over scripts/test-*-structure.sh)

## Decision 2: Companion .md files
- **Question**: Are all 7 bash harnesses accompanied by .md companion files?
- **Resolution**: No — scripts/test-learn-from-bugs-structure.sh has no .md companion; the other 6 do. Only 6 .md files need deletion.
- **Source**: codebase (confirmed by ls scripts/test-*-structure.md)

## Decision 3: Shard membership — Bash targets stay, implementations change
- **Question**: Do the test-harnesses-N shard membership lists change?
- **Resolution**: No. The same 7 Make target names stay in test-harnesses-2/4/5; only the recipe bodies change from `bash scripts/...` to `python3 -m pytest ...`. No shard line edits needed.
- **Source**: codebase (Makefile lines 346, 350, 352)

## Decision 4: Python sharding
- **Question**: Do the new pytest tests need a shard-assignments entry?
- **Resolution**: The new test_skill_structure.py is discovered automatically by `make py-test`; individual per-skill pytest invocations via the Bash shard harnesses do not require shard-assignments entries. No python/shard-assignments.json change.
- **Source**: codebase (python/conftest.py, py-test Makefile recipe)
