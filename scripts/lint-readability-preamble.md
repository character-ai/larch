# lint-readability-preamble.sh contract

## Purpose

Assert that every real `/design` readability amendment site references the shared style preamble at `skills/design/references/readability-style.md`.

The lint prevents prompt-specific style guidance from drifting away from the canonical preamble. It checks only registered amendment sites.

## Interface

```
lint-readability-preamble.sh [--root <repo-or-fixture-root>]
```

`--root` is for the offline harness. Normal callers omit it, so the script checks the current repository.

## Manifest

Rows live in `scripts/lint-readability-preamble.tsv` (five tab-separated columns per data row). The shared awk-based reader contract is documented in `scripts/lint-readability-preamble.tsv.md`. Comment lines and blank lines are skipped; invalid `expected_count` values exit 2.

`variant` is one of:

- `external-prompt` — exact-line counts (`standard`, `sketch`, or `plan-review` via `prompt_kind`)
- `orchestrator-inline` — regex count of the MANDATORY readability directive; optional `step_markers` enforces ≥1 match per listed step body in `skills/design/SKILL.md`

The manifest is an allowlist of real amendment sites. It intentionally excludes the readability source file, this lint, and harness scripts.

## Checked Lines

For `external-prompt` `standard`, the file must contain this exact line (repeated per `expected_count`):

```
Style requirements: `<READABILITY_STYLE>`.
```

For `sketch`, the file must contain this exact prompt line (no backticks). The byte-preserved sketch prompt file may satisfy that either as a literal standalone line or as the escaped `\n...` tail inside a quoted prompt body:

```
Style requirements: <READABILITY_STYLE>.
```

For `plan-review`:

```
Style requirements for finding text and OOS Descriptions: `<READABILITY_STYLE>`.
```

For `orchestrator-inline`, the file must contain lines matching:

```
^\*\*MANDATORY — READ ENTIRE FILE before [^:]+: `skills/design/references/readability-style\.md`\.\*\*$
```

When `step_markers` is non-empty (today: `2b,3b,4,5` on `skills/design/SKILL.md`), each step body between `<!-- step:<id>` markers must contain at least one orchestrator directive match.

## Exit Codes

| Code | Meaning |
|---|---|
| 0 | All manifest rows passed |
| 1 | One or more manifest rows failed |
| 2 | Invalid lint arguments, manifest variant, or TSV `expected_count` |

Failures print stderr lines such as:

```
<path>: missing <variant> readability-style directive
<path>: expected <n> orchestrator-inline readability-style directives, found <m>
<path>: step "<id>": orchestrator-inline step marker not found
<path>: step "<id>": expected >=1 orchestrator-inline readability-style directive in step body, found 0
```

## Edit-in-sync

Update this file, `scripts/lint-readability-preamble.tsv`, `scripts/lint-readability-preamble.tsv.md`, `scripts/test-lint-readability-preamble.sh`, `scripts/test-lint-readability-preamble.md`, `.pre-commit-config.yaml`, and the `Makefile` targets when changing the manifest or accepted line patterns.
