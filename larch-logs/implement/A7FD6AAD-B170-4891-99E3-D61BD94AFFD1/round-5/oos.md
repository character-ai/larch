### FINDING_17: [OUT_OF_SCOPE] risk-integration: skills/design/scripts/test-plan-review-loop.sh:3901
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Design plan-review-loop captures collector stderr but lacks behavioral tail-surfacing test. #3119-style design panel failures might not reach chat if tee/FD routing regresses despite collector unit tests passing. Add plan-review-loop case with failing panel stubs asserting stderr tails on FD 2/4 when collect succeeds.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_18: [OUT_OF_SCOPE] risk-integration: hooks/hooks.json (branch)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Unrelated hook-anti-read-poll expansion ships in the same branch as #3202. Increases CI time and coupling; failures may be attributed to the wrong feature during triage. Split or clearly label hook work; ensure hook harness stays in the same shard as related changes.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### FINDING_24: [OUT_OF_SCOPE] security: scripts/compose-collector-failure-log.sh:66
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Pre-existing raw cat of .diag in failure bundles can include unredacted DIAG_DETAIL snippets. Unrelated to new stderr-tail sections but still leaks agent output snippets into review failure artifacts. Redact or render .diag through the same pipeline as launch-stderr when composing failure logs.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_37: [OUT_OF_SCOPE] **Stdout `KEY=value` contract:** §3.8 runs after all `RESULTS[]` mutations and before `# --- 4. Emit structured results ---`; it only uses `larch_err` / a sig-map temp file, not `emit`/`printf` to stdout. The collector subshell in `collect-findings.sh` keeps stdout (`> "$collector_results_file"`) separate from stderr (`2>"$collector_stderr"`). Harness cases in `scripts/test-collect-agent-results.sh` (dedup/distinct/phase fallback) assert stdout stays free of tail bodies. No stdout-corruption defect found for the scoped invariants.
- **Reviewer**: dyn-fd-contract-output.txt
- **Concern**: - **Stdout `KEY=value` contract:** §3.8 runs after all `RESULTS[]` mutations and before `# --- 4. Emit structured results ---`; it only uses `larch_err` / a sig-map temp file, not `emit`/`printf` to stdout. The collector subshell in `collect-findings.sh` keeps stdout (`> "$collector_results_file"`) separate from stderr (`2>"$collector_stderr"`). Harness cases in `scripts/test-collect-agent-results.sh` (dedup/distinct/phase fallback) assert stdout stays free of tail bodies. No stdout-corruption defect found for the scoped invariants.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_38: [OUT_OF_SCOPE] **`compose-collector-failure-log.sh`:** `_redacted_launch_stderr_body` uses `render_failed_agent_stderr_tail` to the composed log file only; callers redirect script stdout (`collect-findings.sh:233-257`, `plan-review-loop.sh:802-805`). No collector stdout interaction.
- **Reviewer**: dyn-fd-contract-output.txt
- **Concern**: - **`compose-collector-failure-log.sh`:** `_redacted_launch_stderr_body` uses `render_failed_agent_stderr_tail` to the composed log file only; callers redirect script stdout (`collect-findings.sh:233-257`, `plan-review-loop.sh:802-805`). No collector stdout interaction.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_39: [OUT_OF_SCOPE] **`collect-findings.sh` replay:** When `collector_stderr` is empty and `collector_rc=0`, `replay_collector_failed_stderr_tails` re-resolves tails and prints via `_write_failed_stderr_tail_block` to FD 2/4 without the collector’s signature dedup; this is latent (normally §3.8 populates `collector_stderr` first) but worth knowing if replay ever becomes the primary path.
- **Reviewer**: dyn-fd-contract-output.txt
- **Concern**: - **`collect-findings.sh` replay:** When `collector_stderr` is empty and `collector_rc=0`, `replay_collector_failed_stderr_tails` re-resolves tails and prints via `_write_failed_stderr_tail_block` to FD 2/4 without the collector’s signature dedup; this is latent (normally §3.8 populates `collector_stderr` first) but worth knowing if replay ever becomes the primary path.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_44: [OUT_OF_SCOPE] **Verified OK:** `dispatch-with-waterfall.sh:269,284` writes raw bytes only to `${output}.launch-stderr` on disk; every chat/log path checked (`resolve_collector_stderr_tail_file` at `lib-failed-agent-stderr-tail.sh:175-177`, `compose-collector-failure-log.sh:57-58`, `render_failed_agent_stderr_tail` at `lib-failed-agent-stderr-tail.sh:108`) runs `tail | redact-tmpdir-paths.sh | redact-secrets.sh` with spool-then-`head -c` (pipefail-safe at `107-115`). `design-log-publish.sh:302-308` dual-redacts all non-excluded staged files including publishable `*.stderr-tail`; `*.launch-stderr` is not excluded but is redacted on publish, not copied raw. `SECURITY.md:256` publish-time claim matches `design_publish_stage_file`.
- **Reviewer**: dyn-redaction-coverage-output.txt
- **Concern**: - **Verified OK:** `dispatch-with-waterfall.sh:269,284` writes raw bytes only to `${output}.launch-stderr` on disk; every chat/log path checked (`resolve_collector_stderr_tail_file` at `lib-failed-agent-stderr-tail.sh:175-177`, `compose-collector-failure-log.sh:57-58`, `render_failed_agent_stderr_tail` at `lib-failed-agent-stderr-tail.sh:108`) runs `tail | redact-tmpdir-paths.sh | redact-secrets.sh` with spool-then-`head -c` (pipefail-safe at `107-115`). `design-log-publish.sh:302-308` dual-redacts all non-excluded staged files including publishable `*.stderr-tail`; `*.launch-stderr` is not excluded but is redacted on publish, not copied raw. `SECURITY.md:256` publish-time claim matches `design_publish_stage_file`.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_45: [OUT_OF_SCOPE] Raw `*.sidecar` / `*.diag` remain excluded from publish (`design-log-publish.sh:259`) and are outside the new tail feature; `.diag` is still `cat`’d unredacted into composed failure logs (pre-existing pattern).
- **Reviewer**: dyn-redaction-coverage-output.txt
- **Concern**: - Raw `*.sidecar` / `*.diag` remain excluded from publish (`design-log-publish.sh:259`) and are outside the new tail feature; `.diag` is still `cat`’d unredacted into composed failure logs (pre-existing pattern).
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_46: [OUT_OF_SCOPE] `gitleaks` does not scan `larch-logs/`; committed `*.stderr-tail` artifacts rely on publish-time redaction and operator hygiene, as documented in `SECURITY.md`.
- **Reviewer**: dyn-redaction-coverage-output.txt
- **Concern**: - `gitleaks` does not scan `larch-logs/`; committed `*.stderr-tail` artifacts rely on publish-time redaction and operator hygiene, as documented in `SECURITY.md`.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### FINDING_49: [OUT_OF_SCOPE] **Fail-open (scout item 4):** Parse/`jq` failures consistently `exit 0` (`12-13`, `15`, `301-302`, `317-318`, `326`); `emit_reminder` uses `|| true`; no `set -e`. Looks correct.
- **Reviewer**: dyn-hook-blast-radius-output.txt
- **Concern**: - **Fail-open (scout item 4):** Parse/`jq` failures consistently `exit 0` (`12-13`, `15`, `301-302`, `317-318`, `326`); `emit_reminder` uses `|| true`; no `set -e`. Looks correct.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_50: [OUT_OF_SCOPE] **rm/ls/cp false positives (scout item 2):** `bash_segment_task_output_poll_token` requires `bash_has_read_verb` (`66-76`, `101-108`); non-read commands mentioning `tasks/<id>.output` should not count. Harness covers `ls`, `echo cat …`, `jq '…cat…'`, assignment decoys; no in-scope defect found for the cited rm/ls/cp case.
- **Reviewer**: dyn-hook-blast-radius-output.txt
- **Concern**: - **rm/ls/cp false positives (scout item 2):** `bash_segment_task_output_poll_token` requires `bash_has_read_verb` (`66-76`, `101-108`); non-read commands mentioning `tasks/<id>.output` should not count. Harness covers `ls`, `echo cat …`, `jq '…cat…'`, assignment decoys; no in-scope defect found for the cited rm/ls/cp case.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_51: [OUT_OF_SCOPE] **TSV concurrency:** `handle_task_output_poll` / `handle_generic_read_poll` use read-modify-write without locking (`216-245`, `263-291`); overlapping PostToolUse invocations could under-count (miss reminder) rather than block tools—accepted heuristic risk, not introduced solely by the matcher change.
- **Reviewer**: dyn-hook-blast-radius-output.txt
- **Concern**: - **TSV concurrency:** `handle_task_output_poll` / `handle_generic_read_poll` use read-modify-write without locking (`216-245`, `263-291`); overlapping PostToolUse invocations could under-count (miss reminder) rather than block tools—accepted heuristic risk, not introduced solely by the matcher change.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### FINDING_52: [OUT_OF_SCOPE] **Documented parsing gaps:** `hook-anti-read-poll.md` and inline comments note `;`/`&&` splitting inside quotes and unexpanded `VAR=…/tasks/id.output` then `cat "$VAR"` as known limitations; tests pin several false-positive guards.
- **Reviewer**: dyn-hook-blast-radius-output.txt
- **Concern**: - **Documented parsing gaps:** `hook-anti-read-poll.md` and inline comments note `;`/`&&` splitting inside quotes and unexpanded `VAR=…/tasks/id.output` then `cat "$VAR"` as known limitations; tests pin several false-positive guards.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_53: [OUT_OF_SCOPE] **#3202 stderr-tail work** (`lib-failed-agent-stderr-tail.sh`, collector dedup, Claude timeout clamp) is separate from hook blast-radius; not audited here beyond coexisting on the branch.
- **Reviewer**: dyn-hook-blast-radius-output.txt
- **Concern**: - **#3202 stderr-tail work** (`lib-failed-agent-stderr-tail.sh`, collector dedup, Claude timeout clamp) is separate from hook blast-radius; not audited here beyond coexisting on the branch.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

