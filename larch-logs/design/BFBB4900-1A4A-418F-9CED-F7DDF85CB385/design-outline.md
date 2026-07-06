## Proposed Design Outline

### Goals
- Route all 19 `.claude/rules/*.md` files to existing enforcement mechanisms or documentation
- Fix three code-level prerequisites that reference `.claude/rules/` before deletion
- Delete `.claude/rules/` and remove all cross-references to it

### Non-goals
- Adding entries to `ARCHITECTURAL_INVARIANTS.md` (blocked on #6476)
- Routing any rules to `AGENTS.md` as new content
- Creating new lints for advisory rules that already have aspirational G-* coverage

### Approach sketch
- Fix prerequisites first: repoint `check_topology_rule_paths.py`, drop `.claude/rules/*.md` glob in `lint_codex_exec_auth.py`, remove rule-file accounting in `tokens.py`
- Add new `G-*` guideline entries to `ARCHITECTURAL_GUIDELINES.md` for rules without existing twins
- Add slimmed gh-body section to `BASH_AUTHORING.md` plus a new `lint-gh-body-inline.sh` script
- Delete all 19 rule files and the `.claude/rules/` directory
- Update cross-references in `AGENTS.md`, `docs/linting.md`, and `ARCHITECTURAL_GUIDELINES.md` (G-Sec-3 note)

### Surfaces in scope
- `.claude/rules/` (all 19 rule files + directory)
- `python/larch/lint/check_topology_rule_paths.py` (repoint away from RULE_PATH)
- `scripts/test-check-topology-rule-paths.sh` + `.md` (update harness)
- `python/larch/lint/lint_codex_exec_auth.py` (remove `.claude/rules/*.md` glob and base loop)
- `python/larch/report/tokens.py` (remove `.claude/rules/*.md` accounting branch)
- `BASH_AUTHORING.md` (new § 4: gh `--body` / `--notes` file-backed)
- `scripts/lint-gh-body-inline.sh` + `.md` (new lint for inline `gh --body`)
- `Makefile` (new `lint-gh-body-inline` target)
- `ARCHITECTURAL_GUIDELINES.md` (new G-* entries for untwined rules; drop G-Sec-3 rule-file note)
- `AGENTS.md` (remove "Tier 1c: path-triggered Claude Code rules" bullet from Load Semantics)
- `docs/linting.md` (drop `.claude/rules` scan-scope mentions)

### Open questions
- None.
