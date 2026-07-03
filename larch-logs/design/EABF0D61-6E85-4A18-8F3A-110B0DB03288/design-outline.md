## Proposed Design Outline

### Goals
- Restore the dropped security-triage caution ("when unsure, don't file publicly") into `agents/_implementer-base.md`, in a terse form matching the post-#5980 compressed style.
- Regenerate `agents/codex-implementer.md` and `agents/cursor-implementer.md` so the caution appears in all three prompts.
- Keep `generate check` green and the panel-tier token-closure baseline delta at or under +40 tokens.

### Non-goals
- No other prose from the #5980 compression pass gets revisited.
- No changes to other `agents/*.md` reviewer files.
- No new SECURITY.md behavior. This restores existing intended guidance, not new behavior.

### Approach sketch
- Edit the security-findings bullet in the "OOS triage gate before manifest" section of `agents/_implementer-base.md`; append a short uncertain-case clause.
- Run `generate codex-implementer` and `generate cursor-implementer` to propagate the wording into both derivatives.
- Regenerate `python/skill-closure-baseline.json` (`lint skill-closure-growth --write`) since panel-tier token counts grow; verify the delta stays at or under +40 tokens.
- Confirm SECURITY.md already documents the underlying behavior; no edit needed there.

### Surfaces in scope
- `agents/_implementer-base.md`
- `agents/codex-implementer.md` (generated)
- `agents/cursor-implementer.md` (generated)
- `python/skill-closure-baseline.json` (regenerated)

### Open questions
- None.
