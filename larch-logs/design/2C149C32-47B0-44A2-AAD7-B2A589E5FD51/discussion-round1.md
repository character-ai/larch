## Decision 1: Implementation surface
- **Question**: Pre-commit local hook vs. extending agent-lint upstream?
- **Resolution**: Pre-commit local hook — `scripts/lint-gh-body-inline.sh` + sibling `.md`, registered as a `repo: local` hook in `.pre-commit-config.yaml`. Matches existing repo convention (lint-bash32, lint-foreground-markers, lint-readability-preamble, lint-no-raw-stderr-after-quiet-init).
- **Source**: user

## Decision 2: File scope
- **Question**: Lint `.sh`/`.py` only, or also `.md`?
- **Resolution**: `.sh` and `.py` only, per issue text. Markdown reminders for known editors are already covered by `.claude/rules/gh-body-file.md`.
- **Source**: user

## Decision 3: Out-of-scope (must not break / must not pull in)
- **Question**: Should the lint extend coverage to YAML workflows, change the existing `gh-body-file.md` rule, or modify any of the ~30 existing callers it already lists?
- **Resolution**: No. The scope is strictly additive: a new pre-commit hook + sibling docs + Makefile wiring + harness. The path-triggered markdown rule, `.github/workflows/*.yaml` invocations, `agent-lint.toml`, and the existing 30+ callers using `--body-file` are NOT touched.
- **Source**: codebase + issue text

## Decision 4: Strict mode (no path allowlist)
- **Question**: Should the lint exempt the ~30 paths the rule already lists, or apply uniformly?
- **Resolution**: Apply uniformly to all `.sh`/`.py` files. The rule's contract is "always use the file-backed variant"; the lint enforces this contract repo-wide. The rule's `paths:` list is for editor-side reminders, not a structural exemption.
- **Source**: codebase (re-read `.claude/rules/gh-body-file.md`)

## Decision 5: Fixture/test escape hatch
- **Question**: How should test harness fixtures (gh stubs that assert "no inline `--body`") be exempted from triggering the lint?
- **Resolution**: Inline `# lint-gh-body-inline: ok <reason>` suppression comments on the same line, matching the existing precedent (`# lint-bash32: ok <reason>`, `# lint-foreground-markers: ok <reason>`). Confirmed ~9 candidate false-positive lines all share this stub-pattern shape.
- **Source**: codebase

## Decision 6: Hard fail on violation
- **Question**: Should the hook block commits (non-zero exit) or just warn?
- **Resolution**: Hard fail (exit 1) on any violation, matching every other pre-commit lint in this repo. Inline allow-comments are the safety valve.
- **Source**: codebase
