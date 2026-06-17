---
paths: ["scripts/**/*.sh", "skills/**/scripts/**/*.sh", ".claude/skills/**/scripts/**/*.sh", "hooks/**/*.sh"]
---

# Python-First Scripts

New larch script logic should be Python by default. Put the implementation in
`python/` and expose it through `python3 python/cli.py`.

Bash is allowed only for these cases:

- Thin delegation wrappers that set up environment and delegate to
  `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" <domain> <verb> [args...]`.
  Do not call `python/<module>.py` directly from wrappers.
- Claude Code hooks.
- Pre-commit or CI glue.

This rule is forward-looking. Existing Bash is not automatically in scope.

Thin delegation wrappers are glue for new surfaces, not migration cutover shims.
During sh-to-py migration or voluntary ports, follow
[docs/python-migration.md](../../docs/python-migration.md) **No shims** and
recipe step 4, **Cut ALL consumers to direct `cli.py` calls**. Repoint consumers
straight to `cli.py`; do not add forwarding `.sh` stubs.

See [AGENTS.md](../../AGENTS.md) for the repository-wide convention.
