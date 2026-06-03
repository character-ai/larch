# read-plugin-version.sh contract

## Purpose

Read the larch plugin version from `${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json` and emit a single `LARCH_PLUGIN_VERSION=<value>` line for run metadata. If `CLAUDE_PLUGIN_ROOT` is unset, the helper computes the plugin root from its own location (`scripts/..`).

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
- Do not edit `.claude-plugin/plugin.json`; this script is read-only and `.claude-plugin/plugin.json` remains owned by `/release`.
- Emit exactly one stdout line so shell callers can parse it without `eval`.

## Edit-in-sync pointers

| File | Relationship |
|---|---|
| `scripts/larch-log.sh` | Records the plugin version in run manifests. |
| `scripts/test-larch-log.sh` | Regression harness for manifest and batch writes. |
| `scripts/larch-log.md` | Human-readable log contract. |

## Test harness

Covered by `scripts/test-larch-log.sh`, which is wired into `make test-harnesses`.
