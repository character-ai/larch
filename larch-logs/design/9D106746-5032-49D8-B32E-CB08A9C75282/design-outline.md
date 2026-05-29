## Proposed Design Outline

### Goals
- Make SIMPLE the default `/design` tier. No `--hard` ⇒ SIMPLE.
- Keep `--hard` as the only tier flag; it opts into HARD.
- Remove every live-surface mention of `--simple`.

### Non-goals
- No change to SIMPLE or HARD tier behavior (sketches, dialectic, review-run caps).
- No backward compatibility for `--simple` (no alias, no deprecation shim).
- Do not touch immutable history (`larch-logs/**`, dated `CHANGELOG.md`).

### Approach sketch
- SKILL.md Step 0b: delete the no-flag tier-selection gate; default to `design_classification=SIMPLE`.
- Flag parser: drop `--simple`; reject a passed `--simple` with a clear error before Step 0 (never swallow it as feature text).
- `flags.md`: rewrite the tier section to `--hard`-only; collapse the now-vacuous `--simple`/`--hard` mutual-exclusion prose.
- Update the no-flag default provenance (`design_classification_reason` / `_source`) so a flagless run is recorded as the SIMPLE default.
- Docs + `plugin.json` argument hint: `[--hard]` (drop `--simple`).

### Surfaces in scope
- `skills/design/SKILL.md`, `skills/design/references/flags.md`, `skills/design/references/approval-gates.md`
- `README.md`, `docs/{installation-and-setup,issue-anchored-plan,skills,workflow-lifecycle}.md`, `.claude-plugin/plugin.json`
- Tests touching the `--simple` surface: `scripts/test-design-structure.sh`, `skills/design/scripts/test-design-driver.sh` (Step 2b confirms the full list)

### Open questions
- Exact reject-message wording for a passed `--simple` (generic unknown-flag vs. named hint). Leaning generic to honor "remove all mentions". Plan-level detail.
