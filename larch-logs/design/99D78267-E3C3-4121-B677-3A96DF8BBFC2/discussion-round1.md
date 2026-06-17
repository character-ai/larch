## Decision 1: Where the rule lives
- **Question**: Where should the "new larch scripts go in Python" rule live?
- **Resolution**: Add a bullet to the AGENTS.md Conventions section (always loaded), AND add a path-triggered `.claude/rules/*.md` reminder that fires on `.sh` edits (modeled on `shell-strict-mode.md`). Cross-reference `docs/python-migration.md`.
- **Source**: user

## Decision 2: Enforcement scope
- **Question**: Documentation-only, or also add a mechanical lint?
- **Resolution**: Documentation-only. No new lint. "Thin wrapper" is not crisply machine-checkable; enforcement is via reviewers plus the path-triggered reminder.
- **Source**: user

## Decision 3: Thin-wrapper exception definition
- **Question**: How should the rule define the allowed Bash "thin wrapper" exception?
- **Resolution**: Bash stays allowed only for thin wrappers that set up environment and delegate to `python/cli.py` (or a Python module), plus Claude Code hooks (already bash per the migration decision log) and pre-commit/CI glue. All new logic goes in Python.
- **Source**: user

## Decision 4: Retroactivity
- **Question**: Does the rule mandate migrating existing Bash scripts, or only govern new ones?
- **Resolution**: Forward-looking only. The issue says "from now on". No mandate to migrate existing scripts; existing Bash is out of scope. The existing `docs/python-migration.md` playbook still governs voluntary sh-to-py ports.
- **Source**: feature description

## Decision 5: Python constraints to reference
- **Question**: What Python constraints must the rule align with?
- **Resolution**: Stdlib-only, Python >= 3.11, flat `python/` layout, `python/cli.py` as the canonical entrypoint, no shims. These already exist in the `docs/python-migration.md` Decision log; the new rule restates the forward-looking policy and points there.
- **Source**: codebase (docs/python-migration.md)
