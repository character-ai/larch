## Proposed Design Outline

### Goals
- Auto-proceed with a printed warning when exactly one of Codex/Cursor is unavailable.
- Keep the user-confirmation prompt only when both tools are unavailable.
- Preserve all existing non-interactive/autonomous behavior unchanged.

### Non-goals
- Changing the `DEGRADED=true|false` semantics or the per-tool `STATE` outputs.
- Altering runtime waterfall fallback policy.
- Touching non-interactive / cron / autonomous runs.

### Approach sketch
- Add `BOTH_DOWN=true|false` KV to `degraded-tools-gate.sh` output (`true` iff both `CODEX_STATE != ok` AND `CURSOR_STATE != ok`).
- Update `skills/shared/external-reviewers.md` "Degraded-tools gate (Step 0)" to branch on `BOTH_DOWN`: print-and-proceed when `false`, ask as today when `true`.
- Update all four SKILL.md callers to parse `BOTH_DOWN` and follow the same branch.
- Update warning text for the auto-proceed path so it does not say "Continue or abort?".
- Add test cases in `test-degraded-tools-gate.sh` for the new `BOTH_DOWN` output.

### Surfaces in scope
- `scripts/degraded-tools-gate.sh`
- `scripts/degraded-tools-gate.md`
- `scripts/test-degraded-tools-gate.sh`
- `skills/shared/external-reviewers.md`
- `skills/design/SKILL.md` (Step 0a gate block)
- `skills/implement/SKILL.md` (Step 0 gate block)
- `skills/review/SKILL.md` (Step 0 gate block)
- `skills/research/SKILL.md` (Step 0 gate block)

### Open questions
- None.
