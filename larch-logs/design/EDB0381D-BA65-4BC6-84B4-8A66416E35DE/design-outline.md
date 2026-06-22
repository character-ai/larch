## Proposed Design Outline

### Goals
- Add a fence-aware linter that flags two **source-adjacent** ```bash tool-call fences (separated only by blank lines, HTML comments, or short breadcrumb prose) in orchestrator-facing skill `.md` files.
- Support the documented carve-outs (pause-check, recovery-probe, `<task-notification>` wait fences, WRONG/CORRECT example pairs) plus an inline `# lint-consecutive-bash: ok <reason>` suppression.
- Wire it into `make lint` and pre-commit as a hard-fail; make existing files pass via carve-outs and justified suppressions.

### Non-goals
- No refactor of orchestrator logic into `cli.py` verbs in this PR; file OOS for any genuine consecutive-Bash smells.
- No runtime tool-sequence modeling; static source analysis only.
- No new shared Bash library; the linter is Python per the python-first convention.

### Approach sketch
- New `python/lint_consecutive_bash.py` mirroring `lint_skill_invocations.py` (fence-toggle parser, `lint_common.run_file_lint`).
- Glob `skills/*/SKILL.md`, `.claude/skills/*/SKILL.md`, and `skills/*/references/*.md`.
- Classify fences: a `bash`/`sh` fence is a tool call unless it is an example block (info-string or WRONG/CORRECT marker); flag two tool fences with no intervening non-Bash step.
- Apply carve-outs and the inline suppression; add `python/test_lint_consecutive_bash.py`; wire into the `make lint` suite and pre-commit.

### Surfaces in scope
- `python/lint_consecutive_bash.py` (new), `python/test_lint_consecutive_bash.py` (new).
- `Makefile` lint target and the pre-commit config.
- Existing skill `.md` files only for suppression/carve-out tuning, not logic refactor.

### Open questions
- Exact signal for the boundary carve-outs (recognize pause-check / recovery-probe / `<task-notification>` fences by surrounding markers vs. an explicit allowlist). Resolve during plan drafting/review.
