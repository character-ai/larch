# Final Summary Emit Contract

Shared orchestrator-side contract for publishing `final-summary.md` bodies to top chat. Call sites supply the profile, the task-output source when the profile needs one, and the after-action.

## Shared rules

- Emit only the body as plain orchestrator chat markdown.
- When a `Read` fallback is used, write the Read result directly as orchestrator text.
- Never use Bash, Python, or another tool call to extract or print the final-summary body.
- Do NOT paraphrase, summarize, reorder, or add prose between bullets.
- Do NOT condense, collapse, or omit any part of the body (including `### Round N reviewer timing` ASCII Gantt blocks). Do NOT wrap any section in `<details>` or equivalent HTML.
- Do not add prose around the block.
- Do not add post-emit recap prose, artifact bullet recaps, or parenthetical cost paraphrases such as approximate no-cost restatements.
- Preserve the full structured block, including title, mode, duration, cost line with per-agent breakdown, tokens, and bullets.
- The caller supplies the profile, task-output source when applicable, and after-action.

## Caller profile parameters

Callers that use the marker-first profile must bind these values at the call site:

- begin marker token
- end marker token
- task-output source description
- whether extraction is in-context-only
- Read fallback policy: `allowed` with a named path, or `forbidden`
- sidecar follow-on policy: `allowed` via `REPORT_GATE_SIDECARS_FILE`, or `forbidden`
- after-action

## Marker-first profile

Use this profile when the caller names a task-output source that can emit markers. `/design` binds completed background-task `<task-notification>` stdout per the Callsite bindings rows. `/implement` binds captured foreground Bash wrapper stdout, not `<task-notification>`.

1. Locate the first balanced whole-line caller begin/end marker pair in the caller-named task-output source already in the orchestrator context window.
2. Extract the marker body and emit its full body verbatim as plain chat markdown — including all subsections such as `### Round N reviewer timing` ASCII bar charts and the `**Top reviewers**` list. Do NOT collapse, wrap in `<details>`, or omit any part of the marker body.
3. Do not re-read task-output files, stdout captures, result env files, or tmpdir logs to recover markers.
4. Do not scrape markers via Bash or Python.
5. Only when steps 1–2 yield no valid marker body and the caller Read fallback policy is `allowed`, Read the caller-named fallback path when non-empty. When the caller Read fallback policy is `forbidden`, skip Read fallback entirely.
6. Only when the caller sidecar policy is `allowed`, and the completed task-output source includes non-empty `REPORT_GATE_SIDECARS_FILE=<path>`, Read that file and emit its full body verbatim immediately after the final-summary body. When the caller sidecar policy is `forbidden`, skip sidecar follow-on entirely.

## Callsite bindings

| Call site | Markers | Source | In-context-only | Read fallback | Sidecar follow-on | After-action |
| --- | --- | --- | --- | --- | --- | --- |
| `/design` marker-first | `LARCH_FINAL_SUMMARY_BEGIN` / `LARCH_FINAL_SUMMARY_END` | named completed background task `<task-notification>` stdout already in context | `true` | `allowed` on `${FINAL_SUMMARY_PATH:-$DESIGN_TMPDIR/final-summary.md}` when non-empty | `allowed` via `REPORT_GATE_SIDECARS_FILE` | caller-specific continuation |
| `/implement` Step 17 marker-first | `---LARCH-SUMMARY-FINAL-BEGIN---` / `---LARCH-SUMMARY-FINAL-END---` | captured foreground `python/cli.py implement step-16-17` Bash wrapper stdout | `true` | `forbidden` | `forbidden` | write `$IMPLEMENT_TMPDIR/.step17-emitted` only after top-chat emission |
| `/implement` Step 18b marker-first | `---LARCH-SUMMARY-FINAL-BEGIN---` / `---LARCH-SUMMARY-FINAL-END---` | green path: captured foreground `python/cli.py implement step-18-gate-finalize` Bash wrapper stdout when `NEXT_ACTION=finalize-done`; non-green path: captured foreground `step-18.sh --phase finalize` Bash wrapper stdout on stall-recovery and escalation-filing branches | `true` | `forbidden` | `forbidden` | do not write `.step17-emitted` after finalize returns |

## File-only profile

Use this profile when the caller has no task-output-source path.

1. Skip marker extraction entirely; do not scan prior tool output for markers.
2. When `[ -s "${FINAL_SUMMARY_PATH:-$DESIGN_TMPDIR/final-summary.md}" ]`, Read that file and emit its full body verbatim as plain chat markdown.
3. No `REPORT_GATE_SIDECARS_FILE` follow-on unless a caller explicitly names a sidecar source outside this profile.

## Update Triggers

Update this file when final-summary marker names, task-output source bindings, Read fallback policy, sidecar policy, preamble wording, post-emit recap/no-cost paraphrase rules, or orchestrator-text emit rules change.
