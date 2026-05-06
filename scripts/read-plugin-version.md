# read-plugin-version.sh contract

## Purpose

Read the larch plugin version from `${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json` and emit a single `LARCH_PLUGIN_VERSION=<value>` line for anchor-comment metadata. If `CLAUDE_PLUGIN_ROOT` is unset, the helper computes the plugin root from its own location (`scripts/..`).

The helper is best-effort by design: missing `jq`, missing or unreadable `plugin.json`, malformed JSON, null/missing `version`, or path-resolution failures all produce `LARCH_PLUGIN_VERSION=unknown`.

## Interface

```
read-plugin-version.sh
```

No flags are accepted. The optional environment variable `CLAUDE_PLUGIN_ROOT` overrides the computed root.

## Output contract

```
LARCH_PLUGIN_VERSION=<value>
```

The helper always exits 0. Callers must treat the value as display metadata only.

## Invariants

- Do not fail callers because plugin-version metadata is unavailable.
- Do not edit `.claude-plugin/plugin.json`; this script is read-only and `.claude-plugin/plugin.json` remains owned by `/bump-version`.
- Emit exactly one stdout line so shell callers can parse it without `eval`.

## Edit-in-sync pointers

| File | Relationship |
|---|---|
| `scripts/assemble-anchor.sh` | Primary caller; injects the emitted version into the anchor comment's `run-statistics` section. |
| `scripts/test-assemble-anchor.sh` | Regression harness for seed, populated-fragment, and missing-root fallback behavior. |
| `skills/implement/references/anchor-comment-template.md` | Human-readable anchor template documenting the auto-injected row. |

## Test harness

Covered by `scripts/test-assemble-anchor.sh`, which is wired into `make test-harnesses` and available standalone via `make test-assemble-anchor`.
