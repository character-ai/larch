## Proposed Design Outline

### Goals
- Codify a forward-looking policy: write new larch scripts in Python, not Bash.
- Allow Bash only for thin wrappers, Claude Code hooks, and CI/pre-commit glue.
- Make the policy both always-loaded and visible at the moment a `.sh` is edited.

### Non-goals
- No migration of existing Bash scripts; the rule is "from now on".
- No new lint or mechanical enforcement (doc-only).
- No runtime, skill, or shipped-behavior changes.

### Approach sketch
- Add one bullet to the `AGENTS.md` "Conventions" section stating the Python-first policy and the thin-wrapper / hooks / glue exception.
- Add a path-triggered `.claude/rules/python-first-scripts.md` (frontmatter `paths:` on `.sh` globs, modeled on `shell-strict-mode.md`) as the point-of-edit reminder.
- Add a short forward-looking entry to the `docs/python-migration.md` Decision log and cross-link the three surfaces.

### Surfaces in scope
- `AGENTS.md` (Conventions bullet)
- `.claude/rules/python-first-scripts.md` (new rule file)
- `docs/python-migration.md` (Decision log entry / cross-reference)

### Open questions
- None.
