# lint-readability-preamble.sh contract

## Purpose

Assert that every real `/design` readability amendment site references the shared style preamble at `skills/design/references/readability-style.md`.

The lint prevents prompt-specific style guidance from drifting away from the canonical preamble. It checks only registered amendment sites.

## Interface

```
lint-readability-preamble.sh [--root <repo-or-fixture-root>]
```

`--root` is for the offline harness. Normal callers omit it, so the script checks the current repository.

## Manifest Grammar

The script owns a hard-coded manifest of rows:

```
path:variant[:expected-count[:prompt-kind]]
```

`variant` is one of:

- `external-prompt`
- `orchestrator-inline`

`expected-count` declares how many matching readability-style directives
must appear in that file. Rows without a count default to one match.
`prompt-kind` selects the accepted external-prompt line shape when needed.

The manifest is an allowlist of real amendment sites. It intentionally excludes:

- `skills/design/references/readability-style.md`
- `scripts/lint-readability-preamble.sh`
- `scripts/lint-readability-preamble.md`
- `scripts/test-lint-readability-preamble.sh`
- `scripts/test-lint-readability-preamble.md`

Those exclusions keep the lint from passing by matching its own contract text.

## Checked Lines

For `external-prompt`, the file must contain one of these exact lines:

```
Style requirements: `<READABILITY_STYLE>`.
Style requirements for finding text and OOS Descriptions: `<READABILITY_STYLE>`.
```

For `orchestrator-inline`, the file must contain a line matching:

```
^\*\*MANDATORY — READ ENTIRE FILE before [^:]+: `skills/design/references/readability-style\.md`\.\*\*$
```

## Exit Codes

| Code | Meaning |
|---|---|
| 0 | All manifest rows passed |
| 1 | One or more manifest rows failed |
| 2 | Invalid lint arguments or manifest variant |

Failures print one stderr line per row:

```
<path>: missing <variant> readability-style directive
<path>: expected <n> orchestrator-inline readability-style directives, found <m>
```

## Edit-in-sync

Update this file, `scripts/test-lint-readability-preamble.sh`, `scripts/test-lint-readability-preamble.md`, `.pre-commit-config.yaml`, and the `Makefile` targets when changing the manifest or accepted line patterns.
