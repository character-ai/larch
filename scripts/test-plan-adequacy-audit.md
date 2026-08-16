# test-plan-adequacy-audit.sh

Editorial harness for `/implement` Preflight audit wiring.

## Purpose

Pins the split between `scripts/larch.sh implement preflight` and the main-agent plan-adequacy audit.

## Primary files checked

- `skills/implement/SKILL.md`
- `skills/implement/references/preflight-plan-audit.md`
- `skills/implement/references/force-mode.md`
- `crates/larch-cli/src/implement_preflight_commands.rs`
- `crates/larch-cli/tests/implement_admission_migrated_parity.rs`

## Invariants

- The helper owns missing and malformed fallback prose.
- Force bypass grammar and canonical force tokens are pinned in `skills/implement/references/force-mode.md`, not always-loaded `skills/implement/SKILL.md`.
- Full warning and refusal templates are pinned in `implement_preflight_commands.rs`.
- Executable source greps use stable technical tokens, not placeholder-heavy documentation strings.
- Item 4 reads title and body from `$PREFLIGHT_TMPDIR/issue.json`.
- Item 4 reads plan text from `$PREFLIGHT_TMPDIR/plan-from-issue.txt`.
- `audit.txt` is refuse-only. `AUDIT=pass` is returned in chat only.
