## Proposed Design Outline

### Goals
- Remove stale "Claude-only fallback" language from `docs/skills.md` `/status` entry.
- Fix stale one-down/both-down routing description in `docs/external-reviewers.md`.
- Align both docs with the authoritative contract in `skills/shared/external-reviewers.md` and `skills/status/SKILL.md`.

### Non-goals
- No changes to `skills/status/SKILL.md` (already correct).
- No changes to `skills/shared/external-reviewers.md` (already correct).
- No code changes; documentation only.

### Approach sketch
- Patch one sentence in `docs/skills.md` line 179: replace "reduced panel or Claude-only fallback" with language mirroring the SKILL.md step-2 note (one-down → requires operator confirmation + reduced panel; both-down → hard-fail).
- Patch the degraded-tools gate paragraph in `docs/external-reviewers.md` (lines 10): flip the one-down and both-down descriptions to match the shared-contract (one-down requires Continue/Abort; both-down hard-fails without a prompt).
- Run `make lint` after edits.

### Surfaces in scope
- `docs/skills.md` (single sentence edit, line ~179)
- `docs/external-reviewers.md` (one paragraph, lines 10)

### Open questions
- None.
