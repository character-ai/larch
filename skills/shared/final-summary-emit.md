# Final Summary Emit Contract

Shared orchestrator-side contract for publishing `final-summary.md` bodies to top chat. Call sites supply the profile, the completed task-output source when the profile needs one, and the after-action.

## Shared rules

- Emit only the body as plain orchestrator chat markdown.
- When a `Read` fallback is used, write the Read result directly as orchestrator text.
- Never use Bash, Python, or another tool call to extract or print the final-summary body.
- Do NOT paraphrase, summarize, reorder, or add prose between bullets.
- Do not add prose around the block.
- Preserve the full structured block, including title, mode, duration, cost line with per-agent breakdown, tokens, and bullets.
- The caller supplies the profile, task-output source when applicable, and after-action.

## Marker-first profile

Use this profile when a completed background task can emit markers.

1. Locate the first balanced whole-line `LARCH_FINAL_SUMMARY_BEGIN` / `LARCH_FINAL_SUMMARY_END` pair in the completed task `<task-notification>` stdout already in the orchestrator context window.
2. Extract the marker body and emit its full body verbatim as plain chat markdown.
3. Do not re-read task-output files, stdout captures, result env files, or tmpdir logs to recover markers.
4. Do not scrape markers via Bash or Python.
5. If markers are absent or invalid in that in-context notification text, use the Read tool on `${FINAL_SUMMARY_PATH:-$DESIGN_TMPDIR/final-summary.md}` when non-empty.
6. When the completed notification stdout includes non-empty `REPORT_GATE_SIDECARS_FILE=<path>`, Read that file and emit its full body verbatim immediately after the final-summary body.

## File-only profile

Use this profile when the caller has no completed task-output source.

1. Skip marker extraction entirely; do not scan prior tool output for markers.
2. When `[ -s "${FINAL_SUMMARY_PATH:-$DESIGN_TMPDIR/final-summary.md}" ]`, Read that file and emit its full body verbatim as plain chat markdown.
3. No `REPORT_GATE_SIDECARS_FILE` follow-on unless a caller explicitly names a sidecar source outside this profile.

## Update Triggers

Update this file when `/design` final-summary marker names, fallback path, sidecar handling, or orchestrator-text emit rules change.
