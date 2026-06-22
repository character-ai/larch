## Decision 1: "Consecutive Bash" detection model
- **Question**: Does "consecutive Bash" mean source-adjacent fences or a runtime tool sequence?
- **Resolution**: Source-adjacent fences. Flag two ```bash tool-call fences separated only by blank lines, HTML comments, or short breadcrumb prose. Carve-outs plus inline suppressions exclude legit boundaries (pause-check fences, foreground recovery-probe fences, `<task-notification>` wait fences, and WRONG/CORRECT example pairs). Static and predictable; no runtime modeling.
- **Source**: user

## Decision 2: Existing-violation handling
- **Question**: How should existing skill `.md` files be made to pass on the first run?
- **Resolution**: Tune carve-outs for the documented boundary patterns and add justified inline suppressions for any remaining legit pairs. Do NOT refactor orchestrator logic in this PR. File OOS issues for any genuine consecutive-Bash smells surfaced.
- **Source**: user

## Decision 3: File scope
- **Question**: Which skill `.md` files does the linter scan?
- **Resolution**: `skills/*/SKILL.md`, `.claude/skills/*/SKILL.md`, and `skills/*/references/*.md`. The orchestrator Bash fences and the documented carve-out patterns live in references too.
- **Source**: user

## Decision 4: Severity (make lint / pre-commit)
- **Question**: Warning-only or hard-fail?
- **Resolution**: Hard-fail (blocking), consistent with existing `lint_*` linters that return a non-zero exit through `lint_common.run_file_lint`.
- **Source**: codebase

## Decision 5: Suppression comment grammar
- **Question**: What inline-suppression token format should legitimate exceptions use?
- **Resolution**: Follow the repo convention `# lint-<name>: ok <reason>` (mirrors `# lint-bare-grep-probe: ok` and `# lint-bash32: ok`). A reason is required.
- **Source**: codebase
