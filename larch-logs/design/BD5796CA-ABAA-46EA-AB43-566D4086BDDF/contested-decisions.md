### DECISION_1: Step 6 prompt-contract clarification — include in this fix or defer?
- **Chosen**: Defer unless code audit produces textual evidence of a specific mis-trigger in SKILL.md anti-halt or Step 6 prose.
- **Alternative**: Always include — proactively clarify Step 6 as an explicit terminal boundary (Codex's view).
- **Tension**: Codex argues clarifying Step 6 is the simplest contract fix; Cursor argues the anti-halt reminder is paired with `proceed to Step N+1` directives and Step 6 already has no "continue to Step 7" instruction, so the reminder text per se does not direct re-entry into Step 0 — a prompt clarification would not stop runtime causes (stray ScheduleWakeup, delayed SendMessage). Round 1 Decision 3 forbids loosening anti-halt machinery without clear evidence.
- **Impact**: High
- **Affected files**: skills/design/SKILL.md (anti-halt block ~line 30, Step 5/Step 6 region ~line 1015–1035), scripts/test-design-structure.sh, possibly skills/shared/orchestrator-never.md

### DECISION_2: Invocation telemetry — add it or rely on code audit only?
- **Chosen**: Code audit only; no new telemetry in /design.
- **Alternative**: Add lightweight telemetry at Step 0 + Step 6 (run id, issue, argv hash, parent skill, PID/PPID, start/cleanup timestamps, terminal outcome) plus an audit helper that groups larch-logs/design/<RUN_ID>/manifest.json by issue and time (Codex's view).
- **Tension**: Telemetry would enable future audit but expands /design's own footprint, which is the opposite of what the reporter is asking for (they want fewer spurious /design entries, not more instrumentation on every entry). User confirmed logs are flushed before any re-fire, so telemetry committed to larch-logs wouldn't capture the spurious second entry anyway.
- **Impact**: Medium
- **Affected files**: skills/design/SKILL.md (Step 0/Step 6 telemetry blocks in alternative), scripts/ (new audit helper in alternative)
