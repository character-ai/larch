# lint-renderer-substitution-safety.sh - contract

`scripts/lint-renderer-substitution-safety.sh` flags bash parameter substitutions that use a variable replacement in `${var//pattern/replacement}` form.

## Purpose And Callers

The linter catches the bash 5.x `&` replacement-corruption class from issue #3077 Section A. It is run by `make lint-renderer-substitution-safety`, by the pre-commit hook of the same name, and by `scripts/relevant-checks.sh` through scoped pre-commit.

## Inputs And Scope

- Scans `scripts/*.sh` and `skills/*/scripts/*.sh` under `--root` (default: repository root).
- Flags replacement positions that start with a shell variable expansion: `$name` or `${name...}`.
- Excludes ANSI-C escape replacements such as `$'\n'`, which are byte literals rather than user or file data.
- Ignores matches inside quoted heredoc fixture bodies, so harnesses can embed unsafe examples.

## Output

Findings are written to stderr as `<path>:<line>: unsafe ${VAR//pat/$rep} substitution; ...`. Exit 1 when findings exist, 0 otherwise, and 2 for argv errors.

## Waivers

Use `# lint-renderer-safe: ok <reason>` on the same line or immediately preceding line when a callsite is intentionally safe.

## Harness

Run `bash scripts/test-lint-renderer-substitution-safety.sh` or `make test-lint-renderer-substitution-safety`.

## Edit In Sync

Update this file and the harness when the unsafe-substitution pattern, scan scope, waiver convention, or heredoc handling changes.
