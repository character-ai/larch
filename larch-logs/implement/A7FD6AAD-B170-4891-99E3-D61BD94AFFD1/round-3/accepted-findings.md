### FINDING_1: Harness grep mismatches collector stderr emit API
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `scripts/test-run-external-agent.sh` greps for `emit_failed_agent_stderr_tail_file_raw` in `collect-agent-results.sh`, but the collector emits via `_emit_collector_stderr_tail_file` / `larch_err` (no raw `>&2` in collector). The harness traceability check contradicts quiet-init lint and may not fail when the plan expects; acceptance requiring extended run-external-agent harness coverage is not met.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Remove or replace grep with a contract that matches larch_err emission; optionally add a lib quiet emitter shared by collector and tests
  - From cursor-specialist-plan-fidelity-output.txt: Remove or fix the grep assertion to match collector implementation; optionally centralize fence emission through the lib helper


### FINDING_11: Missing E2E test for collect-findings §3.8 tail surfacing
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan expects `collect-findings` to surface collector §3.8 tails on wrapper FD 2 when `collector_rc=0`; `skills/review/scripts/test-collect-findings.sh` only greps source and tests `collect-agent-results.sh` in isolation. Broken tee or `REVIEW_TMPDIR` wiring could ship while CI stays green and `/review` hides external failure tails.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add an end-to-end collect-findings.sh case with failing external fixtures; assert fenced tails on the wrapper's captured FD 2 when collector_rc=0.


### FINDING_18: launch-claude-review success path may replay unredacted stderr
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `scripts/launch-claude-review.sh` (~207–211) success path replays raw `SUBPROCESS_STDERR` when redacted emit returns non-zero; misconfigured install (non-executable `redact-secrets.sh`) during `rc=0` launch with stderr warnings can flush unredacted tokens into orchestrator chat.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Remove unredacted fallback; fail closed with a generic warning or route only through write_failed_agent_stderr_tail / redacted sidecar.


### FINDING_19: compose-collector-failure-log dumps raw `.launch-stderr` with secrets-only redaction
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-stderr-redaction-chain-output.txt
- **Severity**: important
- **Concern**: `scripts/compose-collector-failure-log.sh` (~57–59) copies raw `.launch-stderr` into composed logs; `append-tool-failure.sh --redact` runs only `redact-secrets.sh`, not `redact-tmpdir-paths.sh`. Session tmpdir and operator repo paths in launcher validation stderr can reach `execution-issues.md` while chat tails use dual redaction via `render_failed_agent_stderr_tail`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Pipe composed logs through redact-tmpdir-paths + redact-secrets, or dump render_failed_agent_stderr_tail output instead of cat launch-stderr.
  - From dyn-stderr-redaction-chain-output.txt: Run `.launch-stderr` through `render_failed_agent_stderr_tail` (or `redact-tmpdir-paths.sh | redact-secrets.sh`) inside `dump_section` before writing, or extend `append-tool-failure.sh --redact` to apply the same dual pipeline used at publish time.


### FINDING_21: Waterfall phase fallback may surface stale prior-phase stderr tail
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `scripts/collect-agent-results.sh` (~1459–1488) phase fallback reuses an earlier-phase `.stderr-tail` when the final phase has no tail; a phase-2 failure (tail A) followed by phase-3 failure B with no tail can show tail A as the phase-3 cause in chat.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Restrict fallback to matching signatures or empty final-phase diagnostics; otherwise omit or label stale phase tails.


### FINDING_22: Broken redact tooling silences tails without operator signal
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Missing/non-executable redact scripts disable tails with no operator signal (`lib-failed-agent-stderr-tail.sh` ~73–87); agent fails with only generic verdict visible—same blind spot as pre-#3202.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Emit one larch_err when tail lines enabled but render returns empty due to redact tool failure.


### FINDING_25: Bash hook false negative — quoted `tasks/…output` paths stripped before token extract
- **Reviewer(s)**: dyn-hook-parser-fidelity-output.txt
- **Severity**: important
- **Concern**: `bash_strip_quoted_for_read_verb` removes quoted spans before `extract_task_output_token`; shapes like `cat '/tmp/proj/tasks/testtask123.output'` leave no `tasks/…` token, so poll is not classified—contradicts `hook-anti-read-poll.md` and `test-hook-anti-read-poll.sh` expectations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-hook-parser-fidelity-output.txt: Extract the canonical `tasks/<id>.output` token from the original segment (or from a quote-aware scan) and use quote-stripping only for read-verb detection, not for token presence; align the `.md` contract and harness with whichever behavior you choose.


### FINDING_26: Bash hook false negative — overly broad `echo*` / `printf*` skip
- **Reviewer(s)**: dyn-hook-parser-fidelity-output.txt
- **Severity**: important
- **Concern**: `bash_segment_is_echo_only` treats any segment matching `echo*` or `printf*` as non-poll; segments like `echolocation "$TASK_OUT"` or `printf_debug; cat …/tasks/id.output` skip real second reads of the same task output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-hook-parser-fidelity-output.txt: Match only known no-op prefixes (e.g. `echo `, `echo\t`, `printf ` with word boundaries) or require the segment to be nothing beyond `echo`/`printf` and its arguments.


### FINDING_32: lib stderr-tail spool pipeline fail-open on redactor errors
- **Reviewer(s)**: dyn-stderr-redaction-chain-output.txt
- **Severity**: important
- **Concern**: `render_failed_agent_stderr_tail` uses `set +o pipefail`, discards stderr (`2>/dev/null || true`), and may write non-empty spool to `${output}.stderr-tail` if a redactor fails mid-pipeline—pre-redaction bytes could be replayed to FD 2.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-stderr-redaction-chain-output.txt: Capture the pipeline exit status; on any redactor failure, delete the spool, skip `.stderr-tail` write/emission, and surface only a generic warning (no raw spool bytes).


### FINDING_33: Emitted stderr tail lines lack `sanitize_diagnostic_line`
- **Reviewer(s)**: dyn-stderr-redaction-chain-output.txt
- **Severity**: important
- **Concern**: Redacted tail lines via `larch_err` / `cat "$tail_file" >&2` in `collect-agent-results.sh` and `lib-failed-agent-stderr-tail.sh` skip `sanitize_diagnostic_line` despite `lib-quiet.md` requiring explicit sanitization before forwarding external content; C0 controls/terminal escapes may reach operator chat/transcript.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-stderr-redaction-chain-output.txt: Pipe each tail line through `sanitize_diagnostic_line` before `larch_err` / `printf`, matching `scripts/ci-failed-jobs.sh:80-101`.


### FINDING_4: Waterfall `--summary-only` skips §3.8 stderr tails in live output
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `scripts/dispatch-with-waterfall.sh` runs `collect-agent-results` with `--summary-only`, which skips §3.8 tail emission (`collect-agent-results.sh` ~1427–1429). Waterfall-only or aggregate-failure terminal paths may leave `.stderr-tail` on disk without FD-2 dedup/tails in orchestrator-visible output unless another path full-collects or replays tails.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Emit tails once after waterfall finalization or replay from sidecars when dispatch reports failures
  - From cursor-specialist-correctness-output.txt: Run one full collect after terminal failure or emit tails from dispatch when slot fails terminally


### FINDING_5: Digit-run signature normalization — plan/doc/tests divergence
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `failed_agent_stderr_signature` in `scripts/lib-failed-agent-stderr-tail.sh` (~110–130) does not implement plan-style `[0-9]+` → `#` normalization; `scripts/lib-failed-agent-stderr-tail.md` and contract text overstate or conflict with behavior; harness pins distinct HTTP codes. Reviewers disagree on whether omission is intentional (doc-only) vs required implementation; dedup may fail to collapse line-number/PID-heavy identical root causes or mislead operators.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Document intentional omission of digit normalization in lib-failed-agent-stderr-tail.md
  - From cursor-specialist-correctness-output.txt: Add planned sed digit normalization and harness case
  - From cursor-specialist-correctness-output.txt: Update doc or implement digit normalization
  - From cursor-specialist-edge-cases-output.txt: Update md to match sed normalization rules in lib-failed-agent-stderr-tail.sh
  - From cursor-specialist-plan-fidelity-output.txt: Add sed -E digit-run normalization per plan; update lib-failed-agent-stderr-tail.md and signature harness cases (including HTTP 401/403) to match intended dedup policy


### FINDING_8: collect-findings tees collector stderr to wrong FD under quiet init
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `skills/review/scripts/collect-findings.sh` tees collector stderr to FD 2 after `larch_quiet_init` redirects real stderr to FD 4; with external failures and `collector_rc=0`, §3.8 tails may land in quiet log / `collect-agent-results.log` but not orchestrator-visible stderr/chat.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Mirror plan-review-loop: tee to FD 4 when `LARCH_QUIET_PID=$$` else FD 2; test collect-findings under quiet init


### FINDING_9: Duplicate fenced tails on run-external-agent `--capture-stdout` failure
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: FAILED path in `scripts/run-external-agent.sh` (~297–316) may emit redacted output block and stderr-tail fence from the same merged `OUTPUT_FILE`, producing near-identical duplicate fenced blocks and noisy transcripts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Skip redundant output block when tail sidecar covers the same source
  - From cursor-specialist-edge-cases-output.txt: Skip fenced stderr emit when source equals already-printed output, or prefer .sidecar for the fence


