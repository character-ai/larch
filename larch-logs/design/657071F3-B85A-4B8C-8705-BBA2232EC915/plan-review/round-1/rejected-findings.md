### [Plan Review] FINDING_1

### FINDING_1: cursor-implement stderr may not reach chat (wrong/missing tail source)
- **Reviewer(s)**: Cursor-Arch, Cursor-Edge, unknown-slot
- **Severity**: important
- **Concern**: The plan treats cursor-implement as a `--capture-stdout` lane where `run-external-agent.sh` reliably produces `${TRANSCRIPT_PATH}.stderr-tail`, but `launch-cursor-implement.sh` uses `--capture-stdout-only`, backgrounds the wrapper, and redirects wrapper I/O to `SIDECAR_LOG` (`>SIDECAR_LOG 2>&1`). Agent output is split across `TRANSCRIPT_PATH` / `.diag` while actionable stderr may sit only in `SIDECAR_LOG`. `select_failed_agent_stderr_source` may therefore tail `.diag` or a partial transcript instead of agent stderr; a consumer-only `step2` emit is insufficient if the tail file never gets SIDECAR-sourced bytes. Reviewers disagree whether the fix is an explicit producer write from `SIDECAR_LOG` (mirror codex-implement) versus verify-first / consumer-only to avoid clobbering an already-good `${TRANSCRIPT_PATH}.stderr-tail` from `.diag`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In launch-cursor-implement.sh failure block (mirror codex-implement), add write_failed_agent_stderr_tail from SIDECAR_LOG or _FAILURE_OUTPUT onto TRANSCRIPT_PATH; tighten plan Background and ### UPDATED: launch-cursor-implement.sh to require this producer unless a harness proves SIDECAR-sourced bytes in the tail file.
  - From Cursor-Edge: Verify `${TRANSCRIPT_PATH}.stderr-tail` after failure; if present, consumer-only via `step2-implement.sh`; if absent, write from `${TRANSCRIPT_PATH}.diag` or `$SIDECAR_LOG`, not assume `--capture-stdout`
  - From unknown-slot: Add explicit on-failure write_failed_agent_stderr_tail "$SIDECAR_LOG" "$TRANSCRIPT_PATH" in launch-cursor-implement (mirror codex-implement); do not rely on consumer-only unless verification shows SIDECAR marker bytes in ${TRANSCRIPT}.stderr-tail
  - From unknown-slot: Update the plan to name the actual flag --capture-stdout-only and clarify that both --capture-stdout and --capture-stdout-only modes satisfy the "tail already produced" criterion; confirm that select_failed_agent_stderr_source with capture_stdout_only=true finds ${TRANSCRIPT_PATH}.diag, so no producer write is needed


