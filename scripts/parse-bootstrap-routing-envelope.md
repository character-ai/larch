# parse-bootstrap-routing-envelope.sh

Shared `/implement` Step 0 routing envelope parse (file-first `bootstrap-routing.env` + stdout fallback). **Source only** — do not execute directly.

## Invocation

```bash
. "${CLAUDE_PLUGIN_ROOT}/scripts/parse-bootstrap-routing-envelope.sh"
. "${CLAUDE_PLUGIN_ROOT}/scripts/parse-bootstrap-routing-envelope.sh" --preserve-coder
```

## Inputs

| Input | Required | Notes |
|-------|----------|-------|
| `_inv_out` | yes | Wrapper stdout capture from `implement-bootstrap-invoke.sh`. |
| `IMPLEMENT_TMPDIR` | no | May be empty before parse; re-derived from `_inv_out` when present. |

## Flags

| Flag | Effect |
|------|--------|
| `--preserve-coder` | Dirty-tree resume: `unset` omits `coder` / `coder_fallback` so the operator's implementer selection survives re-parse. |

## Behavior

1. Clear stale volatile routing keys (`unset` list differs with/without `--preserve-coder`).
2. Set `IMPLEMENT_TMPDIR` from `_inv_out`.
3. Parse `$IMPLEMENT_TMPDIR/bootstrap-routing.env` when it is a regular file (symlinks are skipped; stdout fallback still runs).
4. Fill any still-empty keys from `_inv_out` lines.
5. `export` the canonical routing key set.

Malformed lines (empty key, non-identifier key, unknown key) are ignored.

## Primary caller

`skills/implement/SKILL.md` Step 0 (initial + dirty-tree resume), after wrapper `_inv_rc=0`.

## Edit-in-sync

- `scripts/implement-bootstrap-invoke.sh` (envelope key list + `_inv_emit_routing_kv` allowlist)
- `scripts/test-implement-structure.sh` + `scripts/test-implement-structure.md`
- `skills/implement/SKILL.md` Step 0 bash fences
