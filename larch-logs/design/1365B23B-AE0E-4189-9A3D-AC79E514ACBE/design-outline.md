## Proposed Design Outline

### Goals
- Extract the verbosity-control rules common to both skills into one shared file.
- Cut ~8-10 always-loaded lines from each of `skills/design/SKILL.md` and `skills/implement/SKILL.md`.
- Keep each skill's own Preserved/Suppressed category list and design's Step 3 carve-out intact.

### Non-goals
- No behavior change; pure prose extraction and dedup.
- No edits to other skills (review, research), Python, or scripts.
- No topology.tsv or manifest row (shared docs carry none today).

### Approach sketch
- Add `skills/shared/verbosity-control.md`: the 3 universal rules (empty Bash `description`; terse 3-5-word Agent `description`; no prose between tool outputs beyond each skill's listed categories) plus the short closer.
- `skills/design/SKILL.md`: swap the moved rules for a one-line pointer; keep `Only print:`, `Suppressed output:`, Compact reviewer status table, and `Post-notification for Step 3 waits`.
- `skills/implement/SKILL.md`: swap the moved rules for a one-line pointer; keep Preserved/Suppressed lists; drop "; may degrade in very long sessions."
- Pointer style mirrors the existing `Follow shared/progress-reporting.md rules.` precedent.

### Surfaces in scope
- `skills/shared/verbosity-control.md` (new)
- `skills/design/SKILL.md` — Verbosity Control section
- `skills/implement/SKILL.md` — Verbosity Control section
- Verify with `make test-design-structure`, `make test-implement-structure`, `make test-implement-anti-polling-rule`, `make lint`

### Open questions
- None.
