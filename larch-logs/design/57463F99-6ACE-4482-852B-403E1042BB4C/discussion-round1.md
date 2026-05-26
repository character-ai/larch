## Decision 1: Scope of gh subcommands covered
- **Question**: Which gh invocations should the rule guidance cover?
- **Resolution**: All `gh ... --body` and `--notes` arguments. Concretely: `gh pr create`, `gh issue create`, `gh issue comment`, `gh pr comment`, `gh release create --notes`. Out of scope: `git commit -m` and any `gh` invocation that does not accept `--body`/`--notes`.
- **Source**: user

## Decision 2: Mechanism
- **Question**: Rule only, rule + hook, or hook only?
- **Resolution**: Rule only — a single path-triggered Claude Code rule under `.claude/rules/`. No PreToolUse hook.
- **Source**: user

## Decision 3: Path-trigger surface
- **Question**: Which paths should the rule's `paths:` frontmatter cover?
- **Resolution**: PR-adjacent surface only. Concretely the canonical PR-creation files in the larch repo (`AGENTS.md`, `BASH_AUTHORING.md`, `scripts/create-pr.{sh,md}`, `scripts/ship-pr.{sh,md}`, `skills/implement/SKILL.md`, `skills/issue/SKILL.md`, and any equivalents the sketch phase identifies via grep). Not broad `**/*.md`. Not `scripts/**/*.sh`.
- **Source**: user

## Decision 4: --body strictness
- **Question**: Allow short literal `--body "..."` strings, or require `--body-file` always?
- **Resolution**: Always `--body-file`. Strictest enforcement — ban inline `--body "..."` (and `--notes "..."`) entirely. The recommended path is to Write the body to a file first, then pass `--body-file <path>`.
- **Source**: user

## Decision 5: Wrapper integration
- **Question**: Should the rule explicitly point at `scripts/create-pr.sh` as the canonical larch wrapper?
- **Resolution**: Yes. The rule should say: for `gh pr create` in this repo, prefer `scripts/create-pr.sh`; for any other `gh ... --body`/`--notes` invocation, Write a body file first and use `--body-file <path>`.
- **Source**: user

## Decision 6: --title scope
- **Question**: Should the rule extend to `--title` text?
- **Resolution**: No. Rule covers `--body` and `--notes` only. Titles are typically short single-line strings and not the documented failure mode.
- **Source**: user
