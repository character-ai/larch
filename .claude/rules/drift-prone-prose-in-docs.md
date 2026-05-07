---
paths: ["docs/**/*.md", "skills/**/*.md", "scripts/**/*.md", "README.md", "SECURITY.md", "AGENTS.md", "CLAUDE.md", ".github/workflows/*.yaml"]
---

# Drift-Prone Prose in Docs

Prose in markdown and YAML comments goes stale silently. Avoid drift-prone constructs that have repeatedly broken in this repo:

- **Don't write hardcoded counts** in prose ("52 assertions", "5 reviewers", "3 lanes", "22 test-* scripts"). When a count is structurally derived (number of test cases, panel size, generator rows), pull it from a single source of truth — `skills/shared/topology.tsv` for cross-doc topology counts, the test harness itself for assertion counts, the registry walker for generator drift. If a literal must appear inline, mark it with a grep-friendly tag so future maintainers can find every occurrence.
- **Don't reference line numbers in prose** (`SKILL.md:74`, `helpers.sh:198`, `Makefile:148`). Line numbers drift on every edit. Refer by symbol — function name, header text, labeled comment — and let the reader's editor navigate.
- **Don't paste machine-local absolute paths** (`/Users/<name>/larch1/...`). Use repo-relative paths or `${CLAUDE_PLUGIN_ROOT}/...`.
- **When refactoring a script, skill, or step**, grep across `docs/`, `skills/**/SKILL.md`, `README.md`, `SECURITY.md`, and `.github/workflows/` for prose references to the old name, step number, flag name, enum value, or "Step N" anchor. Stale prose pointing at deleted or renamed entities is the #1 source of repeat OOS issues.
