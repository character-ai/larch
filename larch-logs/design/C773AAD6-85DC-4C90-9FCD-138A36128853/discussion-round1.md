## Decision 1: Shared lint engine availability
- **Question**: Has the sibling "Shared lint engine" issue landed?
- **Resolution**: Yes. `python/larch/lint/engine.py` exists with `LintRule`, `Finding`, and `run_rule` interfaces. Build on it.
- **Source**: codebase

## Decision 2: Guideline ID convention
- **Question**: What is the correct ID for G-Prevent-1 per the file's area conventions?
- **Resolution**: `G-Prev-1` under a new `## Prevention discipline` section, following the 4-char abbreviation style (G-Bash, G-Gate, G-Mig, G-Cfg).
- **Source**: codebase

## Decision 3: Structure harness presence
- **Question**: Does the learn-from-bugs structure harness exist?
- **Resolution**: Yes — `python/tests/skills/_structure_learn_from_bugs_specialized.py` with `test_learn_from_bugs_structure_specialized`. Must extend with new field-name pins.
- **Source**: codebase

## Decision 4: Module-manifest files exist?
- **Question**: Do `lint_module_manifest.py` or `lint-module-manifest.json` already exist?
- **Resolution**: Neither exists. Both are new files in this change.
- **Source**: codebase

0 decisions resolved from user; 4 resolved from codebase.
