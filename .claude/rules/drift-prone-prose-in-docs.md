---
paths: ["docs/**/*.md", "skills/**/*.md", "scripts/**/*.md", "README.md", "SECURITY.md", "AGENTS.md", "CLAUDE.md", ".github/workflows/*.yaml"]
---

# Drift-Prone Prose in Docs

Prose in markdown and YAML comments goes stale silently. Avoid recurring
breakage patterns:

- **Don't write hardcoded counts** in prose ("52 assertions",
  "5 reviewers", "3 lanes", "22 test-* scripts"). For derived counts
  (test cases, panel size, generator rows), use one source of truth:
  `skills/shared/topology.tsv` for cross-doc topology counts, the test
  harness for assertion counts, and the registry walker for generator
  drift. If a literal must appear inline, tag it for grep.
- **Don't reference line numbers in prose** (`SKILL.md:74`,
  `helpers.sh:198`, `Makefile:148`). They drift on every edit. Refer by
  symbol — function name, header text, labeled comment — and let the
  editor navigate.
- **Don't paste machine-local absolute paths**
  (`/Users/<name>/larch1/...`). Use repo-relative paths or
  `${CLAUDE_PLUGIN_ROOT}/...`.
- **When refactoring a script, skill, or step**, grep `docs/`,
  `skills/**/SKILL.md`, `README.md`, `SECURITY.md`, and
  `.github/workflows/` for prose references to the old name, step number,
  flag name, enum value, or "Step N" anchor. Stale prose pointing at
  deleted or renamed entities is the #1 repeat OOS source.
