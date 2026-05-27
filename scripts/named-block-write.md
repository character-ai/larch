# named-block-write.sh contract

## Purpose

Edits a named larch marker block in a GitHub issue body. Current marker
registry: `plan`, `design-pause`.

Marker grammar:

```text
<!-- larch:<name>:start -->
...
<!-- larch:<name>:end -->
```

## Interface

```text
named-block-write.sh --marker <name> --issue <N> (--content-file <path> | --delete) [--repo OWNER/REPO]
```

Marker names must match `^[a-z0-9][a-z0-9-]*$` and must be in the registry.
`--delete` and `--content-file` are mutually exclusive.

Empty `--content-file` content still writes start/end markers with no inner
body; this preserves `plan-block-write.sh` semantics. Deletion is explicit:
`--delete` removes the block when present and otherwise writes the unchanged
body back with `MODE=absent-noop`.

## Output Contract

- Success: `WRITTEN=true`, `MODE=appended|replaced|removed|absent-noop`, `MARKERS_PRESENT=true|false` (pre-edit), `BODY_BYTES=<n>`, exit 0.
- Malformed current body: `MALFORMED=multiple-start|multiple-end|start-without-end|end-without-start|end-before-start`, exit 1.
- `gh` failure: `FAILED=true`, `ERROR=...`, exit 2.
- Redaction helper missing / failure: `FAILED=true`, `ERROR=...`, exit 3.

The helper performs single-shot `gh issue view` and `gh issue edit` calls. It
does not retry. The full edited body is piped through
`scripts/redact-secrets.sh` before `gh issue edit --body-file`.

## Callers

- `scripts/plan-block-write.sh` via `--marker plan`
- `scripts/design-pause-save.sh` via `--marker design-pause --content-file`
- `scripts/design-pause-load.sh` via `--marker design-pause --delete`
