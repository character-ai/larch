## Proposed Design Outline

### Goals
- Stop a leaked or stale `deny-edit-write.sh` registration from denying `Write`/`Edit`/`NotebookEdit` when no live `/research` run exists (#6178).
- Keep the full `/tmp`-only deny while a `/research` run is genuinely active.
- Keep the coupled surfaces (frontmatter, deny script, harness, SECURITY.md) in sync.

### Non-goals
- No Claude Code harness-level fix; no upstream repro or report artifact.
- No matcher change: exactly `Edit|Write|NotebookEdit`.
- No weakening of fail-closed path semantics while the gate is active.

### Approach sketch
- Add an activation gate at the top of `scripts/deny-edit-write.sh`: allow (exit 0) unless a fresh activation sentinel exists.
- `/research` writes a PID-keyed sentinel under `~/.cache/larch/` at setup and removes it at cleanup; setup aborts loudly if the sentinel write fails.
- TTL backstop (~6h, `find -mmin`): stale sentinels from crashed runs stop gating.
- Gate ambiguity fails open (activation axis); path ambiguity while gated still fails closed with the byte-identical deny envelope.
- Extend `scripts/test-deny-edit-write.sh` with sentinel absent / present / stale cases.

### Surfaces in scope
- `scripts/deny-edit-write.sh`, `scripts/deny-edit-write.md`
- `scripts/test-deny-edit-write.sh`, `scripts/test-deny-edit-write.md`
- `skills/research/SKILL.md`
- `.claude/rules/research-readonly-hook-coupling.md`, `SECURITY.md`
- Stale prose mentions: `docs/skills.md`, `docs/workflow-lifecycle.md`

### Open questions
- Exact sentinel directory name (new dedicated dir vs `~/.cache/larch/sessions/`).
