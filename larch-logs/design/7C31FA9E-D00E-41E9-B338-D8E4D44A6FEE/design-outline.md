## Proposed Design Outline

### Goals
- Stage 4 of the #3111 rip-out: remove the breadcrumb live-streaming / Family-B fence apparatus from all skill prose and public docs.
- Collapse every live Family-B fence to a plain foreground call to its script (no `&`, monitor, PID capture, `monitor_rc`, `wait`, sentinels, banners, or per-anchor comments).
- Delete the now-orphaned Stage-3 no-op shims so no dead breadcrumb code remains in tree.

### Non-goals
- No script-behavior or runtime changes beyond deleting orphaned shims (Stages 1-3 already removed the machinery).
- No #3063 hardening carry-overs — that is Stage 5 (#3120).
- Do not remove the preserved `larch-logs/<run-id>/breadcrumbs/` forensics directory, the polling-loop ban, or the redaction toolchain.

### Approach sketch
- Sweep the 13 skill `.md` fence files; replace each Family-B fence with the plain foreground invocation of its script.
- Trim breadcrumb/Family-B prose: `BASH_AUTHORING.md` §4 only (keep §1-3, keep the `CLAUDE.md` import); `AGENTS.md` bullets; `SECURITY.md`; `docs/run-logs.md` (keep forensics-dir text); `docs/linting.md`; `orchestrator-never.md`; implement NEVER #16 (remove) and the Family-B half of NEVER #9 (keep the polling-loop/ScheduleWakeup ban).
- Delete `scripts/breadcrumb-monitor.{sh,md}`; drop the two `larch_quiet` no-op shims from `lib-quiet.{sh,md}`; fix the `test-design-structure.sh` reference.
- Update structure tests that assert fence shape; run `make lint` + relevant harnesses to confirm green.

### Surfaces in scope
- `skills/**` SKILL.md + references (design, implement, research, review, review-and-fix, shared); `.claude/rules/*.md` if any reference remains.
- Root: `BASH_AUTHORING.md`, `AGENTS.md`, `SECURITY.md` (`CLAUDE.md` import unchanged).
- `docs/run-logs.md`, `docs/linting.md`, `docs/configuration-and-permissions.md`.
- `scripts/breadcrumb-monitor.{sh,md}`, `scripts/lib-quiet.{sh,md}`, `scripts/test-design-structure.sh`.

### Open questions
- None. Round 1 settled fence shape (plain foreground), exhaustiveness (full sweep), shim deletion, and the preserve set.
