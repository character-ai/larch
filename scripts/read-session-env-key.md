# scripts/read-session-env-key.sh — contract

`scripts/read-session-env-key.sh` is the wrapper around the safe-parsing inline pattern `awk -F= '$1=="KEY"{print $2; exit}' FILE` that `/implement` Step 2.1 uses to read `CURSOR_HEALTHY` / `GEMINI_HEALTHY` (and similar keys) from `$IMPLEMENT_TMPDIR/session-env.sh` without sourcing the file. Sourcing is unsafe because the file's contents originate from environment-probe output; awk-based extraction prevents code execution from a hostile value.

## Inputs

- `--file PATH` (required) — session-env file path. Must be readable.
- `--key KEY` (required) — `KEY` from a `KEY=VALUE` line.
- `--default VALUE` (optional) — value to emit when the key is absent or has an empty value. When omitted, missing/empty keys produce empty stdout (caller applies its own fallback).

## Output

Single line on stdout containing the resolved value (no `KEY=` prefix).

## When to update

Update this file when the session-env grammar changes (e.g., supporting quoted values, multi-line values), when a new key conventionally needs a default, or when the safe-parsing rule evolves. The "no source / eval" rule is load-bearing: any change that introduces shell evaluation against the file MUST update SECURITY.md and the Cross-Skill Health Propagation procedure in SKILL.md Step 0 in the same PR.

## Test harness

No sibling regression harness — the wrapper is a one-line awk delegate. Manual smoke verification at write-time covers presence / absence / `--default` paths.
