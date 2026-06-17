## Proposed Design Outline

### Goals
- Resolve all 6 combined-OOS drift/test items in #4595 in one low-risk PR.
- Reconcile consumer docs/config/prose with current binding larch contracts.
- Close two regression-test coverage gaps (sessionstart-health; design-step1d5 collect).

### Non-goals
- No behavior changes to runtime code paths (docs/config/test-only).
- No reformatting or refactoring of adjacent unrelated lines.
- No new abstractions, helpers, or flags.

### Approach sketch
- Items 1, 2, 4: surgical prose edits to match binding SKILL contracts (re-verify each before editing).
- Item 3: add `Skill(bug)` + `Skill(larch:bug)` to `.claude/settings.json` allowlist, matching existing style.
- Item 5: add a `LARCH_TOKEN_SESSION_ID`-unset regression case to the sessionstart-health harness (exercise line 192, not under `env -i`).
- Item 6: add a non-zero `collect-results` RC regression case to the design-step1d5 harness.

### Surfaces in scope
- `docs/skills.md`, `README.md` (Item 1)
- `skills/implement/SKILL.md` NEVER #5 (Item 2)
- `.claude/settings.json` (Item 3)
- `skills/status/SKILL.md` (Item 4)
- `scripts/test-sessionstart-health.sh` (Item 5)
- `skills/design/scripts/test-design-step1d5.sh` (Item 6)

### Open questions
- None. Item 4 verified stale (both-down hard-fails; copy says Claude-only fallback) -> fix, not drop.
