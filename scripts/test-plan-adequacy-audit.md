# test-plan-adequacy-audit.sh

Editorial harness for `/implement` Preflight audit wiring.

## Purpose

Pins the split between `python3 python/cli.py implement preflight` and the main-agent plan-adequacy audit.

## Primary files checked

- `skills/implement/SKILL.md`
- `skills/implement/references/preflight-plan-audit.md`
- `skills/implement/references/force-mode.md`
- `python3 python/cli.py implement preflight`
- `python/preflight.py`

## Invariants

- The helper owns missing and malformed fallback prose.
- Force bypass grammar and canonical force tokens are pinned in `skills/implement/references/force-mode.md`, not always-loaded `skills/implement/SKILL.md`.
- Full warning and refusal templates are pinned in `python/preflight.py`.
- Executable source greps use stable technical tokens, not placeholder-heavy documentation strings.
- Item 4 reads title and body from `$PREFLIGHT_TMPDIR/issue.json`.
- Item 4 reads plan text from `$PREFLIGHT_TMPDIR/plan-from-issue.txt`.
- `audit.txt` is refuse-only. `AUDIT=pass` is returned in chat only.
