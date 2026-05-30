Structured aggregator output (plain text; merged duplicates; severity = max across sources).

### FINDING_1: Harness grep mismatches collector stderr emit API
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `scripts/test-run-external-agent.sh` greps for `emit_failed_agent_stderr_tail_file_raw` in `collect-agent-results.sh`, but the collector emits via `_emit_collector_stderr_tail_file` / `larch_err` (no raw `>&2` in collector). The harness traceability check contradicts quiet-init lint and may not fail when the plan expects; acceptance requiring extended run-external-agent harness coverage is not met.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Remove or replace grep with a contract that matches larch_err emission; optionally add a lib quiet emitter shared by collector and tests
  - From cursor-specialist-plan-fidelity-output.txt: Remove or fix the grep assertion to match collector implementation; optionally centralize fence emission through the lib helper

### FINDING_2: Collector §3.8 dedup/tail logic inlined (~110 lines)
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Large blocks of dedup and tail resolution are inlined in `scripts/collect-agent-results.sh` (~1426–1537) despite plan intent for tiny call sites; harder to test and evolve stderr surfacing separately from collection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract §3.8 helpers to a sourced lib; leave collect-agent-results.sh with a single emit call

### FINDING_3: Duplicate fenced-block formatting in stderr-tail lib
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/lib-failed-agent-stderr-tail.sh` duplicates fence string formatting between `larch_err` line loop and raw FD2 `cat`; fence strings can drift between foreground and batch paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Consolidate fence emission in the lib (quiet + raw variants)

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

### FINDING_6: Anti-read-poll hook expansion increases PR blast radius
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Large `scripts/hook-anti-read-poll.sh` / `hooks/hooks.json` / `AGENTS.md` expansion is not in #3202 plan scope; harder to bisect stderr surfacing vs polling-hook regressions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Consider splitting hook work to a separate PR or cross-link in CHANGELOG

### FINDING_7: [OUT_OF_SCOPE] run-external-agent failure tails stdout before stderr sidecar
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: On failure with non-empty output file, `scripts/run-external-agent.sh` (~300–306) still tails OUTPUT_FILE (review stdout) before stderr sidecar path; misleading “output (last lines)” label when stderr is sidecar-only. Pre-existing shape.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Pre-existing; only note if tightening failure diagnostics further

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

### FINDING_10: [OUT_OF_SCOPE] Stale `.stderr-tail` sidecar on success path
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Success path in `scripts/run-external-agent.sh` (~325) does not remove stale `.stderr-tail` until next pre-launch rm; long-lived output basename could retain sidecar until relaunch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Optionally rm .stderr-tail on exit 0

### FINDING_11: Missing E2E test for collect-findings §3.8 tail surfacing
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan expects `collect-findings` to surface collector §3.8 tails on wrapper FD 2 when `collector_rc=0`; `skills/review/scripts/test-collect-findings.sh` only greps source and tests `collect-agent-results.sh` in isolation. Broken tee or `REVIEW_TMPDIR` wiring could ship while CI stays green and `/review` hides external failure tails.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add an end-to-end collect-findings.sh case with failing external fixtures; assert fenced tails on the wrapper's captured FD 2 when collector_rc=0.

### FINDING_12: Collector stdout golden coverage gap for §3.8
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `scripts/test-collect-agent-results.sh` checks tails do not leak and `STATUS=FAILED` remain but does not golden-compare full collector stdout; §3.8 regression could change `FAILURE_REASON=` or KV field order without failing dedup assertions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Golden-compare full collector stdout lines (especially FAILURE_REASON=) for failed slots with and without stderr-tail sidecars.

### FINDING_13: Missing run-external-agent integration test for sidecar-first stderr source
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Mode-aware default review (sidecar before diag) is unit-tested in lib harness but not integration-tested through `run-external-agent` on failure; `select_failed_agent_stderr_source` could regress for codex panel default launches while lib-only tests still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add failed default-mode run with distinct .sidecar and .diag content; assert .stderr-tail matches sidecar.
  - From cursor-specialist-plan-fidelity-output.txt: Add a wrapper harness case with .sidecar populated or document lib harness as the canonical mode-order test

### FINDING_14: collect-findings collector hard-fail may double-print diagnostics
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Collector stderr is teed to FD 2 then replayed from log on `collector_rc != 0` (`collect-findings.sh` ~208–222) with no test coverage; hard-fail paths may double-print and mix live tee with redacted replay.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Skip replay when tee was used or add a harness asserting single emission on collector_rc != 0.

### FINDING_15: launch-claude-subprocess harness lacks `.stderr-tail` / `.done` ordering assertion
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-launch-claude-subprocess.sh` does not assert `.stderr-tail` is written before `.done` on agent failure; collector could observe `.done` before `.stderr-tail` under timing pressure without failing CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add ordering assertion (poll for tail before done or compare mtimes) on the failure stub path.

### FINDING_16: [OUT_OF_SCOPE] Implement launchers lack stderr-tail surfacing
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `scripts/launch-codex-*.sh` / `scripts/launch-cursor-*.sh` implement launchers lack sidecar choke point per plan SIMPLE out-of-scope note; `/implement` codex/cursor failures may still lack chat tails despite #3202 for review/design paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Follow-up stderr-source hook for implement launchers (already planned out of scope).

### FINDING_17: [OUT_OF_SCOPE] design-log-publish `.stderr-tail` copy untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: stderr-tail publishability documented but not covered by `test-design-log-publish.sh`; regressions could drop `.stderr-tail` from larch-logs without a targeted test failing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Extend design-log-publish or larch-log write-round harness to assert .stderr-tail copies when present.

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

### FINDING_20: Committed publishable `.stderr-tail` artifacts lack gitleaks backstop
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Publishable stderr-tail artifacts rely on partial `redact-secrets` inside gitleaks-excluded `larch-logs/`; opaque bearer or connection-string stderr can be committed in `*.stderr-tail` without gitleaks backstop (`SECURITY.md` ~256).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Extend redaction patterns for stderr tails and/or gate publish on scan; keep operator guidance in SECURITY.md prominent.

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

### FINDING_23: Implement/non-review lanes still lack stderr-tail surfacing (in-scope documentation)
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Implement/lint-fix lanes still lack stderr-tail surfacing; non-review codex/cursor failures in `/implement` remain verdict-only in chat (distinct from planned OOS launcher hook work but affects operator expectations).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Follow-up hook at implement launchers; document limitation in configuration doc until done.

### FINDING_24: [OUT_OF_SCOPE] Anti-read-poll hook scope vs #3202 stderr work
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Heuristic Bash/Read task-output poll detection on branch is unrelated to stderr tails; possible false positives/negatives on complex shell.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Separate hook-focused review if incidents appear.

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

### FINDING_27: Bash hook `lines=()` array pollutes global namespace
- **Reviewer(s)**: dyn-hook-parser-fidelity-output.txt
- **Severity**: latent
- **Concern**: `extract_bash_task_output_poll_token` uses a global `lines=()` array; fragile if hook is sourced or nested (low impact today when executed as script).
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-hook-parser-fidelity-output.txt: Declare `local lines=()` inside `extract_bash_task_output_poll_token` (Bash 3.2 supports `local` arrays in functions).

### FINDING_28: [OUT_OF_SCOPE] Generic Read poll state keyed by cwd only across sessions
- **Reviewer(s)**: dyn-hook-parser-fidelity-output.txt
- **Severity**: latent
- **Concern**: Pre-existing: generic Read polling keys state with `state-${cwd_hash}.tsv` only, while task-output polling adds `session_hash`; unrelated sessions sharing cwd can share counters and trigger reminders on the third read across sessions.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_29: [OUT_OF_SCOPE] Documented accepted hook parser false-negative shapes
- **Reviewer(s)**: dyn-hook-parser-fidelity-output.txt
- **Severity**: nit
- **Concern**: `hook-anti-read-poll.md` documents accepted gaps (`VAR=…/tasks/id.output` then `cat "$VAR"`, subshell/heredoc, unquoted `;` in strings)—by design, not regressions.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_30: [OUT_OF_SCOPE] Hook fail-open invariant holds
- **Reviewer(s)**: dyn-hook-parser-fidelity-output.txt
- **Severity**: nit
- **Concern**: Hook omits `set -e`, guards parse paths with `|| exit 0`, always ends `exit 0`; parse failures should not block tools.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_31: [OUT_OF_SCOPE] Branch context — intentional `--summary-only` skip and weaker digit dedup
- **Reviewer(s)**: dyn-hook-parser-fidelity-output.txt
- **Severity**: nit
- **Concern**: Reviewer notes #3202 collector dedup intentionally skipped under `--summary-only`; digit-run normalization not implemented by design in harness; not a hook issue.
- **Suggested revisions (informational for voters; coder decides)**:

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

### FINDING_34: Residual orchestrator-transcript influence via stderr-shaped content
- **Reviewer(s)**: dyn-stderr-redaction-chain-output.txt
- **Severity**: latent
- **Concern**: §3.8 places bounded redacted stderr on FD 2 without neutralizing content shaped like larch `KEY=value|…` RESULTS lines, hook JSON, or `<!-- … -->` markers; compromised CLI stderr could influence orchestrator transcript (stdout KV parsing stays safe).
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-stderr-redaction-chain-output.txt: Document this as accepted residual risk in `SECURITY.md` §Failed-agent stderr tails; optionally add a fixed “untrusted subprocess stderr” banner and strip or escape lines matching `^[A-Z_]+=` / `^<!--` before `larch_err`.

### FINDING_35: [OUT_OF_SCOPE] Primary chat path dual redaction implemented correctly
- **Reviewer(s)**: dyn-stderr-redaction-chain-output.txt
- **Severity**: nit
- **Concern**: Positive observation: `render_failed_agent_stderr_tail` applies tail → tmpdir redact → secrets redact → byte cap after redaction; sidecars and design-log publish align with `SECURITY.md:256`.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_36: [OUT_OF_SCOPE] `emit_failed_agent_stderr_tail_raw` inherits fail-open spool behavior
- **Reviewer(s)**: dyn-stderr-redaction-chain-output.txt
- **Severity**: nit
- **Concern**: `run-external-agent.sh` emits already-redacted sidecar with plain `cat` to FD 2; acceptable given sidecar write path but inherits fail-open spool behavior (see in-scope pipefail finding).
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_37: [OUT_OF_SCOPE] `larch_err` re-redacts secrets only; tmpdir scrub on first pass
- **Reviewer(s)**: dyn-stderr-redaction-chain-output.txt
- **Severity**: nit
- **Concern**: Collector tails fine on chat path; compose/append path for raw `.launch-stderr` is the gap (`lib-quiet.sh` secrets-only re-redact).
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_38: [OUT_OF_SCOPE] Gitleaks does not scan `larch-logs/`
- **Reviewer(s)**: dyn-stderr-redaction-chain-output.txt
- **Severity**: nit
- **Concern**: Documented in `SECURITY.md` / `.gitleaks.toml`; committed `*.stderr-tail` depends on redaction quality, not scanner backstop (overlaps in-scope FINDING_20 with different emphasis).
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_39: [OUT_OF_SCOPE] Pre-existing raw `.diag` in same compose redaction path
- **Reviewer(s)**: dyn-stderr-redaction-chain-output.txt
- **Severity**: nit
- **Concern**: `.diag` was already raw-`cat`'d into secrets-only `append-tool-failure.sh --redact`; branch amplifies exposure by adding `.launch-stderr` with same treatment.
- **Suggested revisions (informational for voters; coder decides)**:
