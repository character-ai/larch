### FINDING_1: Model-args failure never writes `.stderr-tail` before early exit
- **Reviewer(s)**: Cursor-Edge, Cursor-Pragmatic, unknown-slot
- **Severity**: important
- **Concern**: On `agent-model-args.sh` failure, `launch-codex-implement.sh` appends to `$SIDECAR_LOG` and exits with `LAUNCHER_EXIT` before the auth-retry loop and the post-loop `write_failed_agent_stderr_tail` block (~347). `${TRANSCRIPT_PATH}.stderr-tail` is never produced, so step2 `emit_bailed` / `emit_failed_agent_stderr_tail_larch_err` no-ops despite actionable sidecar content. The same early-exit pattern exists in `launch-cursor-implement.sh` (~237–248), where `run-external-agent` auto-write never runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Add write_failed_agent_stderr_tail "$SIDECAR_LOG" "$TRANSCRIPT_PATH" || true on the MODEL_ARGS_RC exit path (same as post-loop failure block)
  - From Cursor-Pragmatic: Also call `write_failed_agent_stderr_tail "$SIDECAR_LOG" "$TRANSCRIPT_PATH" || true` on the model-args failure path before its `exit 0`, or extract a small shared helper invoked from every non-success launcher exit that has sidecar content.
  - From unknown-slot: Add `write_failed_agent_stderr_tail "$SIDECAR_LOG" "$TRANSCRIPT_PATH" || true` inside the `if [[ "$MODEL_ARGS_RC" -ne 0 ]]; then` branch (around line 295, after the `cat "$MODEL_ARGS_ERR" >> "$SIDECAR_LOG"` line) in addition to the post-retry-loop placement. Same fix applies to the analogous model-args failure branch in `scripts/launch-cursor-implement.sh:237-248` — that path also exits before run-external-agent is called, so the auto-write by `run-external-agent` cannot fire.


