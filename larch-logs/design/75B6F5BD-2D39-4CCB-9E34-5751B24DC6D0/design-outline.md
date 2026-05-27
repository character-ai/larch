## Proposed Design Outline

### Goals
- Make a degraded-fallback `final-summary.md` distinguishable from a successful rich render via a visible banner inside the body and an HTML comment marker, so the shared post-publish full-body emit surfaces the degradation at top chat.
- Apply the same fix consistently to both `skills/design/scripts/render-final-summary.sh` (`compose_self_fallback`) and `skills/implement/scripts/write-final-report.sh` (`compose_self_fallback`).
- Add regression coverage to both offline harnesses so the markers cannot regress silently.

### Non-goals
- Changing the script's exit code on fallback (must remain 0; callers don't branch on rc).
- Touching the intermediate `--cost-unavailable` retry stage in `write-final-report.sh` — that stage still produces a full render-run-summary body and is already distinguished by `- **Cost**: N/A`.
- Altering invoke_render / run_body_render failure detection logic, or `append_render_warning` / `append-tool-failure.sh` behavior (the warning already lands in `execution-issues.md`).
- Renaming or changing the existing `<!-- larch:run-summary v=1 -->` marker.
- Changing any caller (SKILL.md Step 0b, 5c items 8/10, Final-summary-block fences, ship-pr.sh, refresh-run-logs.sh).

### Approach sketch
- Insert the banner line immediately AFTER the `## .../implement run <RUN_ID> — <OUTCOME>` heading (with a blank line separator) — never before, because `scripts/verify-run-log-completeness.sh` and `.claude/skills/audit-runs/scripts/audit-scan-run.sh` anchor on the first non-empty line matching `RUN_LOG_TERMINAL_OUTCOME_SUFFIX_EGREP`.
- Banner text: `**⚠ Degraded fallback — full renderer failed; see execution-issues.md Warnings.**`.
- HTML marker line: `<!-- larch:final-summary-fallback v1 -->` placed adjacent to the existing `<!-- larch:run-summary v=1 -->` marker (just after it on its own line) so a single grep finds both.
- Apply the same insertion in `compose_self_fallback` in both `render-final-summary.sh` and `write-final-report.sh`. Implement-side change is scoped to the terminal `compose_self_fallback` call (Stage 3); leave the Stage-2 `--cost-unavailable` path untouched.

### Surfaces in scope
- `skills/design/scripts/render-final-summary.sh` — `compose_self_fallback` function only.
- `skills/implement/scripts/write-final-report.sh` — `compose_self_fallback` function only.
- `skills/design/scripts/test-render-final-summary.sh` + sibling `.md` — add fallback-marker assertion case.
- `skills/implement/scripts/test-write-final-report.sh` + sibling `.md` — add fallback-marker assertion case.
- `skills/design/scripts/render-final-summary.md` and `skills/implement/scripts/write-final-report.md` siblings — document the new banner + HTML comment contract.

### Open questions
- None.
