# Final Summary Emit Contract

Shared orchestrator-side contract for publishing `final-summary.md` bodies to top chat. Call sites supply the profile, the source binding when the profile needs one, and the after-action.

## Shared rules

- Emit only the body as plain orchestrator chat markdown.
- When a `Read` path is used, write the Read result directly as orchestrator text.
- Never use Bash, Python, or another tool call to extract or print the final-summary body.
- Do NOT paraphrase, summarize, reorder, or add prose between bullets.
- Do NOT condense, collapse, or omit any part of the body (including `### Round N reviewer timing` ASCII Gantt blocks). Do NOT wrap any section in `<details>` or equivalent HTML.
- Do not add prose around the block.
- Do not add post-emit recap prose, artifact bullet recaps, or parenthetical cost paraphrases such as approximate no-cost restatements.
- Preserve the full structured block, including title, mode, duration, cost line with per-agent breakdown, tokens, and bullets.
- The caller supplies the profile, source binding when applicable, and after-action.

## Caller profile parameters

Callers that use the marker-first or `/design` Read-always readiness profile must bind these values at the call site:

- begin marker token
- end marker token
- source description: task-output, wrapper stdout, or bgjob `DONE` stdout plus result env
- whether extraction is in-context-only, including any required bgjob result-env read
- Read policy: marker fallback `allowed` with a named path, marker fallback `forbidden`, or `/design` required Read from `FINAL_SUMMARY_PATH`
- sidecar follow-on policy: `allowed` via `REPORT_GATE_SIDECARS_FILE`, or `forbidden`
- after-action

## `/design` Read-always readiness profile

Use this profile for `/design` final `bgjob wait` `DONE` stdout and the matching bgjob result env.

1. Parse `FINAL_SUMMARY_PATH=<path>` from final `bgjob wait` `DONE` stdout already in the orchestrator context window, or from the matching `$DESIGN_TMPDIR/bgjob/<step>.result.env` after `BGJOB_RC=0` and required-KV validation.
2. Confirm whole-line `LARCH_FINAL_SUMMARY_BEGIN` and `LARCH_FINAL_SUMMARY_END` markers are present as a readiness signal only. The marker body is expected to be empty.
3. Do not extract or emit summary bodies from marker pairs on `/design` paths.
4. When `FINAL_SUMMARY_PATH` is non-empty and the path names a non-empty file, use the Read tool on that path and emit the full file body verbatim as plain chat markdown, including all subsections such as `### Round N reviewer timing` ASCII bar charts and the `**Top reviewers**` list. Do NOT collapse, wrap in `<details>`, or omit any part of the file body.
5. Do not re-read task-output files, stdout captures, unrelated result env files, or tmpdir logs to recover markers. Do not re-read those files to recover summary bodies. The only result-env read is the caller's required bgjob result env used for `BGJOB_RC=0` and `FINAL_SUMMARY_PATH` validation.
6. Do not scrape markers via Bash or Python.
7. Only when the caller sidecar policy is `allowed`, and the caller source or matching result env includes non-empty `REPORT_GATE_SIDECARS_FILE=<path>`, Read that file and emit its full body verbatim immediately after the final-summary body. When the caller sidecar policy is `forbidden`, skip sidecar follow-on entirely.

## Marker-first profile

Use this profile when the caller names a source that can emit markers with a non-empty body. `/implement` binds captured foreground Bash wrapper stdout, not `<task-notification>`.

1. Locate the first balanced whole-line caller begin/end marker pair in the caller-named source already in the orchestrator context window.
2. Extract the marker body and emit its full body verbatim as plain chat markdown — including all subsections such as `### Round N reviewer timing` ASCII bar charts and the `**Top reviewers**` list. Do NOT collapse, wrap in `<details>`, or omit any part of the marker body.
3. Do not re-read task-output files, stdout captures, result env files, or tmpdir logs to recover markers.
4. Do not scrape markers via Bash or Python.
5. Only when steps 1–2 yield no valid marker body and the caller Read fallback policy is `allowed`, Read the caller-named fallback path when non-empty. When the caller Read fallback policy is `forbidden`, skip Read fallback entirely.
6. Only when the caller sidecar policy is `allowed`, and the caller source includes non-empty `REPORT_GATE_SIDECARS_FILE=<path>`, Read that file and emit its full body verbatim immediately after the final-summary body. When the caller sidecar policy is `forbidden`, skip sidecar follow-on entirely.

## Callsite bindings

| Call site | Markers | Source | In-context-only | Read fallback | Sidecar follow-on | After-action |
| --- | --- | --- | --- | --- | --- | --- |
| `/design` Read-always readiness | `LARCH_FINAL_SUMMARY_BEGIN` / `LARCH_FINAL_SUMMARY_END` readiness only; marker body expected empty | final `bgjob wait` `DONE` stdout plus matching `$DESIGN_TMPDIR/bgjob/<step>.result.env` after `BGJOB_RC=0` and required-KV validation | `true` after the caller's required result-env read | required Read of parsed `FINAL_SUMMARY_PATH=<path>` when non-empty | `allowed` via `REPORT_GATE_SIDECARS_FILE` | caller-specific continuation |
| `/implement` Step 17 marker-first | `---LARCH-SUMMARY-FINAL-BEGIN---` / `---LARCH-SUMMARY-FINAL-END---` | captured foreground `python/cli.py implement step-16-17` Bash wrapper stdout | `true` | `forbidden` | `forbidden` | write `$IMPLEMENT_TMPDIR/.step17-emitted` only after top-chat emission |
| `/implement` Step 18b marker-first | `---LARCH-SUMMARY-FINAL-BEGIN---` / `---LARCH-SUMMARY-FINAL-END---` | green path: captured foreground `python/cli.py implement step-18-gate-finalize` Bash wrapper stdout when `NEXT_ACTION=finalize-done`; non-green path: captured foreground `step-18.sh --phase finalize` Bash wrapper stdout on stall-recovery and escalation-filing branches | `true` | `forbidden` | `forbidden` | do not write `.step17-emitted` after finalize returns |

## File-only profile

Use this profile when the caller has no source path.

1. Skip marker extraction entirely; do not scan prior tool output for markers.
2. When `[ -s "${FINAL_SUMMARY_PATH:-$DESIGN_TMPDIR/final-summary.md}" ]`, Read that file and emit its full body verbatim as plain chat markdown.
3. No `REPORT_GATE_SIDECARS_FILE` follow-on unless a caller explicitly names a sidecar source outside this profile.

## Update Triggers

Update this file when final-summary marker names, bgjob `DONE` stdout or result-env source bindings, Read fallback policy, sidecar policy, preamble wording, post-emit recap/no-cost paraphrase rules, or orchestrator-text emit rules change.
