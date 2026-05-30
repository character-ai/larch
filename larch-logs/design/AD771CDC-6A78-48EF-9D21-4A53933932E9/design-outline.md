## Proposed Design Outline

### Goals
- On every non-zero codex/cursor/claude subprocess exit, surface the last N (default 30) redacted stderr lines to chat.
- Make reviewer-failure root causes recoverable from the transcript after publish-exclusion and tmpdir cleanup.
- Keep the change additive: the existing verdict line, `.diag`, and the collector `FAILURE_REASON` single-line contract stay byte-stable.

### Non-goals
- No bespoke edits to every `launch-*-*.sh`; centralize at shared choke points.
- No change to success-path behavior — stay quiet on exit 0 (including empty output on success).
- No new transient-vs-permanent failure classification (that is a separate concern).

### Approach sketch
- Add one shared helper: tail N lines from the correct stderr source, redact via `redact-secrets.sh`, cap at 5 KB.
- `run-external-agent.sh`: on non-zero exit (incl. timeout 124) write a redacted+capped tail sidecar from the stderr source (`.sidecar` for codex/cursor, merged output in capture mode).
- `collect-agent-results.sh`: emit that tail as a bounded multi-line block to stdout (the reliable "to chat" surface), separate from single-line `FAILURE_REASON`.
- `launch-claude-review.sh`: surface the same tail from its captured claude-stderr temp file on non-zero exit.
- New env var `LARCH_FAILED_AGENT_STDERR_TAIL_LINES` (default 30; `0` disables).

### Surfaces in scope
- `scripts/run-external-agent.sh`, `scripts/collect-agent-results.sh`, `scripts/launch-claude-review.sh`
- One shared lib for tail+redact+cap, plus its sibling `.md` and regression harness
- `docs/configuration-and-permissions.md` (new env var) and affected `.md` siblings

### Open questions
- Whether the shared helper lives in the existing `lib-external-launcher-common.sh` or a new dedicated lib — settled in the plan step.
