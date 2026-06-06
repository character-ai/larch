## Proposed Design Outline

### Goals
- Render uncaptured exit codes as `unknown` (not a misleading `0`) in every stall-report surface.
- Surface the already-sanitized `bail_reason` in the report body so dispatch-failures name the failing envelope check.
- Keep the sanitization model, allowlist parity, and the offline harness intact.

### Non-goals
- No fix to the actual Step-2 dispatch failure or the classifier's phase/step derivation.
- No operational recovery of the stuck #3550 run.
- No new raw evidence in reports; the sanitization boundary is unchanged.

### Approach sketch
- Add a `safe_exit_code_value` helper mirroring `safe_step_value` / `safe_phase_value`; preserve the `unknown` distinction from `classify` through `compose_body_content` and the chat-print path.
- Add a `bail_reason` row to the report body/comment/chat-print, sourced from the existing sanitized `safe_bail_reason_value`.
- Update the allowlist TSV, the doc surface table, and the `lint` parity surface in lockstep.
- Reconcile the `BAIL_REASON` enum description in `stall-recovery-report.md` to match the code's actual allowlist.

### Surfaces in scope
- `skills/implement/scripts/stall-recovery-report.sh`
- `skills/implement/scripts/stall-recovery-report-allowlists.tsv`
- `skills/implement/scripts/stall-recovery-report.md`
- `skills/implement/scripts/test-stall-recovery-report.sh`

### Open questions
- Exit-code representation: emit non-numeric `unknown` from `classify` directly, vs. keep the machine `EXIT_CODE` KV numeric and add a separate "captured?" signal — resolve in the plan after checking downstream `EXIT_CODE` consumers.
