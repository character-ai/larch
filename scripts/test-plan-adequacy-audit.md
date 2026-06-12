# test-plan-adequacy-audit.sh

Editorial harness for `/implement` Preflight audit wiring.

## Purpose

Pins the split between `scripts/implement-preflight.sh` and the main-agent plan-adequacy audit.

## Primary files checked

- `skills/implement/SKILL.md`
- `skills/implement/references/preflight-plan-audit.md`
- `scripts/implement-preflight.sh`
- `scripts/implement-preflight.md`

## Invariants

- The helper owns missing and malformed fallback prose.
- Full warning and refusal templates are pinned in `scripts/implement-preflight.md`.
- Executable source greps use stable technical tokens, not placeholder-heavy documentation strings.
- Item 4 reads title and body from `$PREFLIGHT_TMPDIR/issue.json`.
- Item 4 reads plan text from `$PREFLIGHT_TMPDIR/plan-from-issue.txt`.
- `audit.txt` is refuse-only. `AUDIT=pass` is returned in chat only.
