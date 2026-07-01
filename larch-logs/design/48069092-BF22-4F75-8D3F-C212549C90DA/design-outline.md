## Proposed Design Outline

### Goals
- Reduce prose density in `skills/shared/design-background-wait.md` by roughly 15% estimated tokens (bytes/4), zero behavior change.
- Preserve the three cited anchors (`## Immediate-background wait rule`, `## Step 3 task notification boundary`, `## Step 3 post-notification sequence`) and every sentinel/literal string pinned by `scripts/test-implement-anti-polling-rule.sh` and `scripts/test-design-structure.sh`.
- Keep both harnesses green without editing the harnesses themselves.

### Non-goals
- No restructuring of headings: no merging, splitting, or removing sections (including `## Step 4 post-notification sequence` and `## Update Triggers`).
- No change to any consumer file (`skills/design/SKILL.md`, `AGENTS.md`, `skills/shared/orchestrator-never.md`, harness scripts) — scope is the shared file only.
- No behavior change: sentinel names, timeouts, `NEXT_ACTION`/`STEP*` grammar, and quoted literal strings stay byte-identical.

### Approach sketch
- In-place sentence-level prose tightening only, matching the precedent style from sibling task #5876 (`finalize-step5.md`): shorten qualifying clauses, cut redundant words, merge sentences repeating the same qualifier.
- Preserve every backtick-quoted token, file path, and issue-number citation verbatim; only touch connective prose around them.
- Keep one paragraph per subsection as today; no bullet-list conversion.
- After editing, regenerate `python/skill-closure-baseline.json` via `make regen-skill-closure-baseline` so the /design closure ratchet reflects the smaller file (matches #5876 precedent).

### Surfaces in scope
- `skills/shared/design-background-wait.md`
- `python/skill-closure-baseline.json` (regenerated, not hand-edited)

### Open questions
- None.
