# lint-skill-md-flag-signature.sh - contract

`scripts/lint-skill-md-flag-signature.sh` checks fenced shell invocations in public skill prompts against the shipped script flag signatures.

## Purpose And Callers

The linter catches SKILL.md to script flag drift from issue #3077 Section B. PR #3024 reintroduced flags in `skills/design/SKILL.md` without updating `scripts/write-run-params.sh`; this linter prevents that class from recurring. It is run by `make lint-skill-md-flag-signature`, by pre-commit, and by relevant-checks through scoped pre-commit.

## Inputs And Scope

- Scans `skills/**/SKILL.md` only.
- Inside fenced `bash`, `sh`, and `shell` blocks, assembles logical commands across trailing-backslash continuation lines before extracting flags.
- Recognizes target scripts addressed as `${CLAUDE_PLUGIN_ROOT}/scripts/<name>.sh`, `${CLAUDE_PLUGIN_ROOT}/skills/<skill>/scripts/<name>.sh`, or absolute paths containing `/scripts/<name>.sh`.
- Resolves target scripts at runtime and checks for matching `--<flag>)` case arms.

Reference files under `skills/*/references/*.md` are not scanned in this initial implementation.

## Output

Findings are written to stderr as `<skill-md-path>:<line>: invocation uses --<flag> but <script-path> does not declare it`. Missing target scripts are warnings and do not fail the run. Exit 1 when mismatches exist, 0 otherwise, and 2 for argv errors.

## Waivers

Use `# lint-skill-md-flag-signature: ok <reason>` on the same logical command or immediately preceding line.

## Harness

Run `bash scripts/test-lint-skill-md-flag-signature.sh` or `make test-lint-skill-md-flag-signature`.

## Edit In Sync

Update this file and the harness when adding new script invocation patterns to recognize, changing scan scope, or changing the waiver convention.
