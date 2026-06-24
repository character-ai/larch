# Review Round 1

- Mode: `diff`
- 2 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Harness omits hooks.json SessionStart registration for sweep-design-logs.sh
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The `test-sweep-design-logs` harness exercises only the script body and does not pin `hooks/hooks.json` SessionStart registration for `scripts/sweep-design-logs.sh`. A future edit can remove or miswire the hook entry (matcher `startup|resume|clear|compact`, command path, timeout `10`) while `make test-sweep-design-logs` and `make lint` stay green; consumers stop running the sweep hook with no regression signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add a jq-based hooks.json registration case mirroring scripts/test-hook-progress-report.sh (command ${CLAUDE_PLUGIN_ROOT}/scripts/sweep-design-logs.sh, matcher startup|resume|clear|compact, timeout 10).
  - From codex-specialist-correctness-output.txt: Add a jq check for matcher startup|resume|clear|compact, command ${CLAUDE_PLUGIN_ROOT}/scripts/sweep-design-logs.sh, type command, and timeout 10
  - From cursor-specialist-edge-cases-output.txt: Add a jq-based hooks.json case asserting command path, matcher startup|resume|clear|compact, and timeout 10 (mirror test-hook-progress-report.sh).
  - From codex-specialist-edge-cases-output.txt: Add a jq assertion that validates command path, matcher, and timeout.
  - From cursor-specialist-testing-output.txt: Add a jq-based hooks.json registration case like scripts/test-hook-progress-report.sh asserting hooks/hooks.json:69-78 registers scripts/sweep-design-logs.sh with correct matcher and timeout.
  - From codex-specialist-testing-output.txt: Add a jq registration case for hooks/hooks.json SessionStart matcher startup|resume|clear|compact, command ${CLAUDE_PLUGIN_ROOT}/scripts/sweep-design-logs.sh, and timeout 10.


### FINDING_2: SECURITY.md contradicts synchronous TMPDIR debug-log write
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `SECURITY.md` claims the hook writes no files while also documenting (or implying) a synchronous TMPDIR debug log write. Auditors relying on the no-files claim miss the foreground `: >"$SWEEP_LOG"` truncate at `scripts/sweep-design-logs.sh:17-18` and may underestimate local temp-file exposure under permissive `TMPDIR`/umask. Documentation should distinguish no repo/session/advisory artifact writes from the per-invocation TMPDIR debug log (not surfaced to session context), and remove the contradictory no-files claim.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Rephrase to repo/session-artifact scope only; explicitly document the per-invocation TMPDIR debug log as the sole hook-side file write, not surfaced to session context.
  - From codex-specialist-correctness-output.txt: Remove the writes-no-files claim, clarify no repo/session advisory artifacts are written, and document the TMPDIR debug log plus /dev/null fallback
  - From cursor-specialist-edge-cases-output.txt: Clarify no repo/session advisory writes; document the TMPDIR debug log explicitly and remove the contradictory no-files claim.
  - From codex-specialist-edge-cases-output.txt: Reword to distinguish no repo/session advisory writes from the TMPDIR debug log write.
  - From codex-specialist-testing-output.txt: Clarify that the hook writes no repo/session/advisory artifacts, but does create or truncate the per-invocation TMPDIR debug log before redirecting sweep output there.


