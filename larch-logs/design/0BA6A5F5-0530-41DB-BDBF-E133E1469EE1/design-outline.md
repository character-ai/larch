## Proposed Design Outline

### Goals
- Unify the implement-path marker tokens to `LARCH_FINAL_SUMMARY_BEGIN` / `LARCH_FINAL_SUMMARY_END` so they match the shared anchor.
- Rewrite NEVER #17, Step 17 main prose, Step 17 cross-reference, and Step 18b in `skills/implement/SKILL.md` to reference `skills/shared/final-summary-emit.md` instead of spelling out the extraction algorithm inline.
- Update structural test pins in `scripts/test-implement-structure.sh` and `scripts/test-render-cost-line-callsites.sh` to verify the new, shorter prose.

### Non-goals
- No changes to the shared anchor's existing profiles (marker-first, file-only) beyond the update-trigger entry.
- No changes to `python/design_lifecycle.py` or design SKILL.md.
- No refactoring of surrounding implement steps beyond the four prose blocks named in the issue.

### Approach sketch
- Change `SUMMARY_BEGIN` / `SUMMARY_END` constants in `python/closeout.py` and the `printf` statements in `skills/implement/scripts/step-18.sh`.
- Rewrite the four SKILL.md prose blocks to say "follow the marker-first profile in `skills/shared/final-summary-emit.md`" with a site-specific source clause and the implement-unique sentinels (`.step17-emitted`, missing-marker warning, no-Read-fallback).
- Update `skills/implement/scripts/step-18.md` and the five structural test pins that currently require the old marker literal or old prose.
- Update `skills/implement/scripts/test-step-18.sh` assertions for the new marker strings.

### Surfaces in scope
- `python/closeout.py` (SUMMARY_BEGIN / SUMMARY_END constants)
- `skills/implement/scripts/step-18.sh` (printf marker statements)
- `skills/implement/scripts/test-step-18.sh` (count_literal assertions)
- `skills/implement/scripts/step-18.md` (marker token documentation)
- `skills/implement/SKILL.md` (NEVER #17, Step 17 prose, Step 17 cross-reference, Step 18b)
- `scripts/test-implement-structure.sh` (structural marker and prose pins)
- `scripts/test-render-cost-line-callsites.sh` (grep pins for SKILL.md prose)

### Open questions
- None.
