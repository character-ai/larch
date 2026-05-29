## Proposed Design Outline

### Goals
- Stage 3 of the 5-piece breadcrumb rip-out: remove the monitor contract at the scripts/lint layer (drop the streaming-redaction wrapper, strip `LARCH_BREADCRUMB_*`/sentinel/paired-PID plumbing from `lib-quiet.sh`, shrink the foreground-marker lint + tests to the polling-loop ban only).
- Keep the tree CI-green **and** every live workflow runnable after this piece alone, before Stage 4 (#3119) lands.
- Preserve secret redaction and the committed quiet-log forensics bridge.

### Non-goals
- No skill-fence collapse (`skills/**`, `.claude/**`, `.claude/rules/*.md`), no `BASH_AUTHORING.md §4` removal, no `AGENTS.md`/`SECURITY.md`/`docs/**` trims — all Stage 4 (#3119).
- No #3063 hardening carry-overs — Stage 5 (#3120).
- No removal of `redact-secrets.sh --streaming` (surviving consumers: `lib-larch-log.sh` + the rewired `larch_err`).

### Approach sketch
- Rewrite `breadcrumb-monitor.sh` as a no-op shim (parse args, exit 0) so the 13 still-live fences keep `wait`-propagating until Stage 4 deletes them; keep a minimal `.md` sibling.
- Delete `lib-redact-streaming.sh`; rewire `lib-quiet.sh`'s `larch_quiet_redact_diagnostic_stream` to call `redact-secrets.sh --streaming` directly; remove sentinel/paired-PID/SURFACED/FD-3 plumbing + `emit_breadcrumb` remnants.
- Shrink `lint-foreground-markers.sh` + its harness + `test-implement-anti-polling-rule.sh` to the polling-loop ban only; delete `test-breadcrumb-monitor*` / `test-background-monitor-wait.sh`.
- Clean the one internal executable consumer `assess-plan-round.sh` (drop monitor call + breadcrumb exports; rely on its existing `wait`).
- Update `Makefile`, `agent-lint.toml`, `scripts/relevant-checks.sh`, grep-based structure tests, and the `env -u`/`unset LARCH_PAIRED_PID_FILE` breadcrumb barriers in Family-B runner/dispatch writers.

### Surfaces in scope
- `scripts/breadcrumb-monitor.*` (→ shim), `scripts/lib-redact-streaming.*` (delete), `scripts/lib-quiet.*`, `scripts/lint-foreground-markers.*`, `scripts/test-lint-foreground-markers.sh`, `scripts/test-implement-anti-polling-rule.*`, `scripts/test-breadcrumb-monitor*`, `scripts/test-background-monitor-wait.sh`.
- `skills/design/scripts/assess-plan-round.sh` (+ `test-assess-plan-round.sh` / `test-dispatch-plan-assessors.sh`).
- `Makefile`, `agent-lint.toml`, `scripts/relevant-checks.sh`, grep-based structure tests; Family-B writer scripts carrying `LARCH_PAIRED_PID_FILE` set/unset + `larch_quiet_write_paired_pid_file` barriers.

### Open questions
- None. Interim-window handling (no-op shim) and `larch_err` redaction (preserve via direct call) were settled in Round 1.
