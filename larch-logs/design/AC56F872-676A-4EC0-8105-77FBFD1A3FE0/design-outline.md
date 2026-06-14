## Proposed Design Outline

### Goals
- Add explicit NEVER rules prohibiting Monitor for one-shot completion in `/implement` and `/design` orchestrators.
- Cover the premature-notification recovery case: re-launch one `Bash run_in_background` task, never fall back to Monitor.
- Pin the new rules with structural test assertions.

### Non-goals
- Fix the live run that triggered the bug (BC8DDA64) — no code change to runtime scripts.
- Renumber or restructure existing NEVER items in implement SKILL.md.
- Fix the stale "NEVER #9" reference in AGENTS.md (pre-existing, out of scope).
- Add rules to `skills/shared/orchestrator-never.md` (issue scopes to the two orchestrators only).

### Approach sketch
- Augment AGENTS.md Conventions bullet with one sentence on premature-notification recovery.
- Extend `/implement` SKILL.md NEVER #8 in-place with an explicit Monitor prohibition and recovery guidance.
- Add Anti-pattern #4 to `/design` SKILL.md Anti-patterns section.
- Add two `check()` calls to `scripts/test-implement-anti-polling-rule.sh` pinning the new literals.
- Update `scripts/test-implement-anti-polling-rule.md` to document the new assertions.

### Surfaces in scope
- `AGENTS.md` (Conventions section, Monitor anti-polling bullet)
- `skills/implement/SKILL.md` (NEVER #8)
- `skills/design/SKILL.md` (Anti-patterns section)
- `scripts/test-implement-anti-polling-rule.sh`
- `scripts/test-implement-anti-polling-rule.md`

### Open questions
- None.
