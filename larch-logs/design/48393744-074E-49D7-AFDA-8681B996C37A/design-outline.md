## Proposed Design Outline

### Goals
- Add `skills/bug/SKILL.md` as a public plugin skill that investigates a described bug and files a comprehensive GitHub issue via `/issue`
- Produce an issue body with summary, reproduction scenario, root cause, affected files, and suggested fix(es) — sufficient context for `/design` to proceed without additional research
- Keep the skill small and focused: parse description, investigate codebase, compose body, call `/issue`

### Non-goals
- No `--no-dedup` flag and no other flags in the initial version
- Not a replay tool — no CI log parsing, no error-log analysis; the user describes the bug in prose
- Not a full research harness — no multi-lane parallel agents, no validation panel

### Approach sketch
- Single-file skill: `skills/bug/SKILL.md` with a 3-step flow (parse → investigate → file)
- Investigation is inline orchestration (Bash + Read/Grep/Glob tool calls in the SKILL.md body) — no external reviewer dispatch
- Body composition is inline LLM work; the composed markdown is passed to `/issue` in single mode
- `/issue` receives the structured body via `--body-file` (temp file) and a descriptive title derived from the bug description
- Sentinel file (`$BUG_TMPDIR/issue-completed.sentinel`) verifies the child ran before cleanup

### Surfaces in scope
- `skills/bug/SKILL.md` (new file)
- `scripts/test-anti-halt-banners.sh` — must be updated to add `bug` to the orchestrator MUST-have-banner list

### Open questions
- None.
